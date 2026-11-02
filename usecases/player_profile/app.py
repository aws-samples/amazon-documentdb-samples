import os
import sys
import json
import time
import logging
from random import Random

from pymongo import MongoClient, DESCENDING, ReturnDocument
from pymongo.errors import ConnectionFailure, DuplicateKeyError, ServerSelectionTimeoutError
from flask import Flask, request, jsonify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

DB_NAME = "player_profile_store"
COLLECTION_NAME = "players"

XP_PER_LEVEL = 1000          # level = 1 + xp // XP_PER_LEVEL (derived on the server, never client-supplied)
MAX_XP_PER_EVENT = 10000     # upper bound on a single progression event
MAX_INVENTORY_STACKS = 100   # cap on distinct item stacks per player (keeps the document bounded)
RECENT_GRANT_IDS = 100       # how many grant IDs are remembered for retry-safe (idempotent) grants

SEED_COUNT = int(os.environ.get("SEED_COUNT", "2000"))   # total players after seeding (anchors + generated)
SEED_BATCH = 500

_client = None


def _sanitize_error(e: Exception) -> str:
    if isinstance(e, (ValueError, KeyError)):
        return str(e)
    return "An internal error occurred. Check the server logs for details."


def get_config() -> dict:
    """Read the cluster connection string (as provided by the DocumentDB console)."""
    uri = os.environ.get("DOCDB_URI")
    if not uri:
        logger.error("Missing required environment variable DOCDB_URI. See README.md for the expected format.")
        sys.exit(1)
    return {"uri": uri}


def get_client():
    """Return a singleton MongoClient, verified with a ping (retries with backoff)."""
    global _client
    if _client is not None:
        return _client
    config = get_config()
    max_retries, retry_delay = 3, 1
    for attempt in range(max_retries):
        client = MongoClient(
            config["uri"],
            retryWrites=False,
            appname="player-profile-store-sample",
            maxPoolSize=10,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000,
        )
        try:
            client.admin.command("ping")
            _client = client  # only cache a client that passed the ping
            logger.info("Connected to DocumentDB")
            return _client
        except (ConnectionFailure, ServerSelectionTimeoutError):
            client.close()
            if attempt == max_retries - 1:
                logger.error("Failed to connect after %d attempts", max_retries)
                raise
            logger.warning("Connection attempt %d failed, retrying in %ds...", attempt + 1, retry_delay)
            time.sleep(retry_delay)
            retry_delay *= 2


def get_collection():
    return get_client()[DB_NAME][COLLECTION_NAME]


def ensure_indexes(collection) -> None:
    """Create indexes once at startup. Each index backs a query issued below."""
    # Every per-player read/update
    collection.create_index("playerId", unique=True, name="idx_playerId_unique")
    # GET /players?displayName=...  (display names are unique)
    collection.create_index("displayName", unique=True, name="idx_displayName_unique")
    # GET /leaderboard (top-N by xp)
    collection.create_index([("xp", DESCENDING)], name="idx_xp_desc")
    logger.info("Indexes ensured on collection '%s'.", collection.name)


def level_for_xp(xp: int) -> int:
    return 1 + xp // XP_PER_LEVEL


def _json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def _parse_limit(default: int, maximum: int) -> int:
    """Parse ?limit= as an integer clamped to [1, maximum]; raises ValueError (-> 400) if not an integer."""
    raw = request.args.get("limit")
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError("limit must be an integer") from None
    return max(1, min(value, maximum))


def _positive_int(value, name, maximum):
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ValueError(f"{name} must be an integer between 1 and {maximum}")
    return value


@app.route("/players", methods=["POST"])
def create_player():
    """Create a player profile document."""
    data = _json_body()
    if data is None:
        return jsonify({"success": False, "message": "Request body must be a JSON object"}), 400
    try:
        xp = data.get("xp", 0)
        if isinstance(xp, bool) or not isinstance(xp, int) or not 0 <= xp <= MAX_XP_PER_EVENT:
            raise ValueError(f"xp must be an integer between 0 and {MAX_XP_PER_EVENT}")
        achievements, settings = data.get("achievements", []), data.get("settings", {})
        if (
            not isinstance(achievements, list)
            or len(achievements) > 100
            or not all(isinstance(a, str) and len(a) <= 64 for a in achievements)
        ):
            raise ValueError("achievements must be a list of up to 100 short strings")
        if not isinstance(settings, dict):
            raise ValueError("settings must be an object")
        doc = {
            "playerId": data["playerId"],
            "displayName": data["displayName"],
            "xp": xp,
            "level": level_for_xp(xp),
            "inventory": [],
            "achievements": achievements,
            "settings": settings,
        }
        if not isinstance(doc["playerId"], str) or not isinstance(doc["displayName"], str):
            raise ValueError("playerId and displayName must be strings")
        get_collection().insert_one(doc)
        return jsonify({"success": True})
    except DuplicateKeyError:
        return jsonify({"success": False, "message": "playerId or displayName already exists"}), 400
    except (ValueError, KeyError, TypeError) as e:
        return jsonify({"success": False, "message": f"Invalid input: {_sanitize_error(e)}"}), 400
    except Exception as e:
        logger.error("Error in create_player: %s", e)
        return jsonify({"success": False, "message": _sanitize_error(e)}), 500


@app.route("/players/<player_id>", methods=["GET"])
def get_player(player_id):
    """Load a single player document (Player 360) by key."""
    try:
        doc = get_collection().find_one({"playerId": player_id}, {"_id": 0, "recentGrantIds": 0})
        if not doc:
            return jsonify({"success": False, "message": "Player not found"}), 404
        return jsonify(doc)
    except Exception as e:
        logger.error("Error in get_player: %s", e)
        return jsonify({"success": False, "message": _sanitize_error(e)}), 500


@app.route("/players", methods=["GET"])
def find_player_by_name():
    """Look a player up by display name (unique index)."""
    name = request.args.get("displayName")
    if not name:
        return jsonify({"success": False, "message": "displayName query parameter is required"}), 400
    try:
        doc = get_collection().find_one(
            {"displayName": name}, {"_id": 0, "playerId": 1, "displayName": 1, "level": 1}
        )
        if not doc:
            return jsonify({"success": False, "message": "Player not found"}), 404
        return jsonify(doc)
    except Exception as e:
        logger.error("Error in find_player_by_name: %s", e)
        return jsonify({"success": False, "message": _sanitize_error(e)}), 500


@app.route("/leaderboard", methods=["GET"])
def leaderboard():
    """Top-N players by xp (bounded to 100, served by the xp index)."""
    try:
        limit = _parse_limit(10, 100)
    except ValueError as e:
        return jsonify({"success": False, "message": f"Invalid input: {e}"}), 400
    try:
        cursor = (
            get_collection()
            .find({}, {"_id": 0, "playerId": 1, "displayName": 1, "level": 1, "xp": 1})
            .sort("xp", DESCENDING)
            .limit(limit)
        )
        return jsonify({"results": list(cursor)})
    except Exception as e:
        logger.error("Error in leaderboard: %s", e)
        return jsonify({"success": False, "message": _sanitize_error(e)}), 500


@app.route("/players/<player_id>/inventory", methods=["POST"])
def grant_item(player_id):
    """Grant an item, retry-safe and atomic.

    The caller supplies a unique `grantId`. If the same grantId is sent again (for example after a
    timeout), the grant is not applied twice. Existing stacks are incremented in place with the
    positional `$` operator; new stacks are appended only if the item is not already present and
    the player is under the stack cap.
    """
    body = _json_body()
    try:
        if body is None:
            raise ValueError("Request body must be a JSON object")
        item, grant_id = body.get("item"), body.get("grantId")
        if not isinstance(item, str) or not item or not isinstance(grant_id, str) or not grant_id:
            raise ValueError("item and grantId are required strings")
        qty = _positive_int(body.get("qty", 1), "qty", 1000)
        rarity = body.get("rarity", "common")
        if not isinstance(rarity, str):
            raise ValueError("rarity must be a string")
    except ValueError as e:
        return jsonify({"success": False, "message": f"Invalid input: {e}"}), 400

    remember = {"recentGrantIds": {"$each": [grant_id], "$slice": -RECENT_GRANT_IDS}}
    not_applied = {"recentGrantIds": {"$ne": grant_id}}
    try:
        players = get_collection()
        if players.count_documents({"playerId": player_id, "recentGrantIds": grant_id}, limit=1):
            return jsonify({"success": True, "duplicate": True})

        for _ in range(2):  # second pass covers a concurrent first-grant of the same item
            # 1) Existing stack: increment in place
            result = players.update_one(
                {"playerId": player_id, "inventory.item": item, **not_applied},
                {"$inc": {"inventory.$.qty": qty}, "$push": remember},
            )
            if result.matched_count:
                return jsonify({"success": True})
            # 2) New stack: append only if absent and under the cap
            result = players.update_one(
                {
                    "playerId": player_id,
                    "inventory.item": {"$ne": item},
                    f"inventory.{MAX_INVENTORY_STACKS - 1}": {"$exists": False},
                    **not_applied,
                },
                {"$push": {"inventory": {"item": item, "rarity": rarity, "qty": qty}, **remember}},
            )
            if result.matched_count:
                return jsonify({"success": True})

        if players.count_documents({"playerId": player_id}, limit=1) == 0:
            return jsonify({"success": False, "message": "Player not found"}), 404
        return jsonify({"success": False, "message": "Inventory is full or grant already applied"}), 409
    except Exception as e:
        logger.error("Error in grant_item: %s", e)
        return jsonify({"success": False, "message": _sanitize_error(e)}), 500


@app.route("/players/<player_id>/inventory/consume", methods=["POST"])
def consume_item(player_id):
    """Consume items atomically. The `qty >= requested` check is part of the update filter,
    so concurrent requests cannot drive a stack negative."""
    body = _json_body()
    try:
        if body is None or not isinstance(body.get("item"), str):
            raise ValueError("item is a required string")
        qty = _positive_int(body.get("qty", 1), "qty", 1000)
    except ValueError as e:
        return jsonify({"success": False, "message": f"Invalid input: {e}"}), 400
    try:
        players = get_collection()
        result = players.update_one(
            {"playerId": player_id, "inventory": {"$elemMatch": {"item": body["item"], "qty": {"$gte": qty}}}},
            {"$inc": {"inventory.$.qty": -qty}},
        )
        if result.matched_count == 0:
            return jsonify({"success": False, "message": "Player not found or insufficient quantity"}), 409
        players.update_one({"playerId": player_id}, {"$pull": {"inventory": {"qty": {"$lte": 0}}}})
        return jsonify({"success": True})
    except Exception as e:
        logger.error("Error in consume_item: %s", e)
        return jsonify({"success": False, "message": _sanitize_error(e)}), 500


@app.route("/players/<player_id>/progress", methods=["PUT"])
def add_progress(player_id):
    """Award xp atomically with `$inc`; level is derived from xp on the server.

    In a real game this endpoint is called by the authoritative game server, never by the client.
    `$max` makes the level update monotonic and safe under concurrent awards.
    """
    body = _json_body()
    try:
        if body is None:
            raise ValueError("Request body must be a JSON object")
        xp = _positive_int(body.get("xp"), "xp", MAX_XP_PER_EVENT)
    except ValueError as e:
        return jsonify({"success": False, "message": f"Invalid input: {e}"}), 400
    try:
        players = get_collection()
        updated = players.find_one_and_update(
            {"playerId": player_id},
            {"$inc": {"xp": xp}},
            projection={"_id": 0, "xp": 1},
            return_document=ReturnDocument.AFTER,
        )
        if updated is None:
            return jsonify({"success": False, "message": "Player not found"}), 404
        level = level_for_xp(updated["xp"])
        players.update_one({"playerId": player_id}, {"$max": {"level": level}})
        return jsonify({"success": True, "xp": updated["xp"], "level": level})
    except Exception as e:
        logger.error("Error in add_progress: %s", e)
        return jsonify({"success": False, "message": _sanitize_error(e)}), 500


# ---------------------------------------------------------------------------
# Sample data: hand-written anchor players (seed_data.json) plus deterministic generated players
# ---------------------------------------------------------------------------

_ADJECTIVES = ["Swift", "Iron", "Silent", "Crimson", "Lunar", "Rapid", "Frost", "Neon", "Shadow", "Golden"]
_NOUNS = ["Falcon", "Knight", "Raven", "Titan", "Ranger", "Wolf", "Mage", "Pilot", "Hunter", "Drifter"]
_ITEMS = [
    ("iron_sword", "common"), ("wood_shield", "common"), ("med_kit", "common"), ("arrow_bundle", "common"),
    ("mana_potion", "common"), ("steel_helm", "rare"), ("frost_bow", "rare"), ("ember_staff", "rare"),
    ("shadow_cloak", "epic"), ("plasma_rifle", "epic"), ("dragon_blade", "legendary"),
]
_ACHIEVEMENTS = ["tutorial_done", "first_blood", "survivor_100", "raid_boss", "explorer", "crafter", "top_100_season5", "veteran"]
_REGIONS = ["us-east", "us-west", "eu-west", "eu-central", "ap-south", "ap-northeast"]


def _generate_players(count: int, first_number: int, rng: Random):
    for i in range(count):
        n = first_number + i
        xp = rng.randint(0, 56000)   # below the top anchor player so the leaderboard leader is stable
        yield {
            "playerId": f"p-{n}",
            "displayName": f"{rng.choice(_ADJECTIVES)}{rng.choice(_NOUNS)}{n}",
            "xp": xp,
            "level": level_for_xp(xp),
            "inventory": [
                {"item": name, "rarity": rarity, "qty": rng.randint(1, 10 if rarity == "common" else 2)}
                for name, rarity in rng.sample(_ITEMS, k=rng.randint(0, 6))
            ],
            "achievements": rng.sample(_ACHIEVEMENTS, k=rng.randint(0, 4)),
            "settings": {"region": rng.choice(_REGIONS), "crossplay": rng.random() < 0.6},
        }


def seed_if_empty(collection):
    """Load the anchor players, then generate more (fixed PRNG seed, so every run is identical)."""
    if collection.count_documents({}, limit=1) > 0:
        return
    docs = []
    seed_path = os.path.join(os.path.dirname(__file__), "seed_data.json")
    if os.path.exists(seed_path):
        with open(seed_path, "r", encoding="utf-8") as f:
            docs = json.load(f)
    else:
        logger.warning("Seed file %s not found; generating players only.", seed_path)
    docs.extend(_generate_players(max(0, SEED_COUNT - len(docs)), 10000, Random(42)))
    for i in range(0, len(docs), SEED_BATCH):
        collection.insert_many(docs[i:i + SEED_BATCH], ordered=False)
    logger.info("Inserted %d sample documents", len(docs))


def cleanup():
    """Drop the collection this sample created."""
    get_collection().drop()
    logger.info("Dropped collection '%s.%s'", DB_NAME, COLLECTION_NAME)


if __name__ == "__main__":
    try:
        if "--cleanup" in sys.argv:
            cleanup()
            sys.exit(0)
        collection = get_collection()
        ensure_indexes(collection)
        seed_if_empty(collection)
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error("Cannot start application - DocumentDB connection failed: %s", e)
        logger.error("Please check your connection settings and ensure DocumentDB is accessible")
        sys.exit(1)

    # Binds to localhost by default. This sample has NO authentication, so do not expose it.
    # Set FLASK_DEBUG=1 only for local development (the debugger allows arbitrary code execution).
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    logger.info("Starting web interface on http://%s:5000", host)
    app.run(debug=debug, host=host, port=5000)
