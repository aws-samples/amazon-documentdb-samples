import os
import re
import sys
import json
import time
import logging
from datetime import datetime, timedelta, timezone
from random import Random

from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure, DuplicateKeyError, ServerSelectionTimeoutError
from flask import Flask, request, jsonify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

DB_NAME = "personalization_store"
COLLECTION_NAME = "shopper_profiles"

RECENT_VIEWS_MAX = 20          # recently viewed SKUs kept in the profile
RECENT_EVENT_IDS_MAX = 50      # event IDs remembered for retry-safe (idempotent) tracking
PROFILE_TTL_DAYS = 180         # profiles inactive for this long are expired automatically
CATEGORY_PATTERN = re.compile(r"^[a-z0-9_-]{1,40}$")   # safe field name for affinities.<category>

# Fields a caller may write through PUT /shoppers/<id>
WRITABLE_PROFILE_FIELDS = {"preferences", "segments", "cart"}

# Bounds for PUT /shoppers/<id> values
MAX_STR_LEN = 100
MAX_SEGMENTS = 20
MAX_PREFERENCES = 20
MAX_CART_ITEMS = 50
MAX_CART_QTY = 1000

SEED_COUNT = int(os.environ.get("SEED_COUNT", "2000"))   # total shoppers after seeding (anchors + generated)
SEED_BATCH = 500

_client = None


# Returned for unexpected server errors; details go to the server log only.
INTERNAL_ERROR = "An internal error occurred. Check the server logs for details."


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
            appname="personalization-store-sample",
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
    """Create indexes once at startup. Each index backs a query or lifecycle rule below."""
    # Every per-shopper read/update
    collection.create_index("shopperId", unique=True, name="idx_shopperId_unique")
    # GET /shoppers?segment=<name>
    collection.create_index("segments", name="idx_segments")
    # Data minimization: expire profiles that have been inactive for PROFILE_TTL_DAYS
    collection.create_index(
        [("lastActiveAt", ASCENDING)],
        expireAfterSeconds=PROFILE_TTL_DAYS * 86400,
        name="idx_lastActiveAt_ttl",
    )
    logger.info("Indexes ensured on collection '%s'.", collection.name)


def _json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def _parse_limit(default: int, maximum: int):
    """Parse ?limit= as an integer clamped to [1, maximum].

    Returns (limit, None) on success or (None, error_message) if it is not an integer.
    """
    raw = request.args.get("limit")
    if raw is None:
        return default, None
    try:
        value = int(raw)
    except ValueError:
        return None, "limit must be an integer"
    return max(1, min(value, maximum)), None


def _is_short_str(v, maximum=MAX_STR_LEN) -> bool:
    return isinstance(v, str) and 0 < len(v) <= maximum


def _validate_profile_fields(data: dict):
    """Light type and size checks for the allowlisted writable fields.

    Returns an error message, or None if the fields are valid.
    """
    if "segments" in data:
        seg = data["segments"]
        if not isinstance(seg, list) or len(seg) > MAX_SEGMENTS or not all(_is_short_str(x, 40) for x in seg):
            return f"segments must be a list of at most {MAX_SEGMENTS} strings (1-40 characters)"
    if "preferences" in data:
        pref = data["preferences"]
        if (not isinstance(pref, dict) or len(pref) > MAX_PREFERENCES or not all(
                _is_short_str(k, 40) and not k.startswith("$") and "." not in k
                and (isinstance(v, (int, float, bool)) or (isinstance(v, str) and len(v) <= MAX_STR_LEN))
                for k, v in pref.items())):
            return (
                f"preferences must be an object of at most {MAX_PREFERENCES} scalar values "
                f"(strings up to {MAX_STR_LEN} characters)")
    if "cart" in data:
        cart = data["cart"]
        if (not isinstance(cart, list) or len(cart) > MAX_CART_ITEMS or not all(
                isinstance(i, dict) and set(i) == {"sku", "qty"} and _is_short_str(i["sku"], 60)
                and isinstance(i["qty"], int) and not isinstance(i["qty"], bool)
                and 1 <= i["qty"] <= MAX_CART_QTY for i in cart)):
            return (
                f"cart must be a list of at most {MAX_CART_ITEMS} objects with a string sku and integer qty "
                f"between 1 and {MAX_CART_QTY}")
    return None


@app.route("/shoppers/<shopper_id>", methods=["GET"])
def get_shopper(shopper_id):
    """Return the shopper preference / behavior profile."""
    try:
        doc = get_collection().find_one({"shopperId": shopper_id}, {"_id": 0, "recentEventIds": 0})
        if not doc:
            return jsonify({"success": False, "message": "Shopper not found"}), 404
        return jsonify(doc)
    except Exception:
        logger.exception("Error in get_shopper")
        return jsonify({"success": False, "message": INTERNAL_ERROR}), 500


@app.route("/shoppers/<shopper_id>", methods=["PUT"])
def update_shopper(shopper_id):
    """Create or update allowlisted profile fields (preferences, segments, cart)."""
    data = _json_body()
    if data is None:
        return jsonify({"success": False, "message": "Request body must be a JSON object"}), 400
    unknown = set(data) - WRITABLE_PROFILE_FIELDS
    if unknown:
        return jsonify({"success": False, "message": f"Fields not writable: {sorted(unknown)}"}), 400
    error = _validate_profile_fields(data)
    if error:
        return jsonify({"success": False, "message": f"Invalid input: {error}"}), 400
    try:
        get_collection().update_one(
            {"shopperId": shopper_id},
            {"$set": {**data, "lastActiveAt": datetime.now(timezone.utc)}},
            upsert=True,
        )
        return jsonify({"success": True})
    except Exception:
        logger.exception("Error in update_shopper")
        return jsonify({"success": False, "message": INTERNAL_ERROR}), 500


@app.route("/shoppers/<shopper_id>", methods=["DELETE"])
def delete_shopper(shopper_id):
    """Erase a shopper profile (for example to honor a deletion request)."""
    try:
        result = get_collection().delete_one({"shopperId": shopper_id})
        if result.deleted_count == 0:
            return jsonify({"success": False, "message": "Shopper not found"}), 404
        return jsonify({"success": True})
    except Exception:
        logger.exception("Error in delete_shopper")
        return jsonify({"success": False, "message": INTERNAL_ERROR}), 500


@app.route("/shoppers", methods=["GET"])
def list_by_segment():
    """List shoppers in a segment (bounded to 100, minimal projection)."""
    segment = request.args.get("segment")
    if not segment:
        return jsonify({"success": False, "message": "segment query parameter is required"}), 400
    limit, error = _parse_limit(25, 100)
    if error:
        return jsonify({"success": False, "message": f"Invalid input: {error}"}), 400
    try:
        cursor = get_collection().find(
            {"segments": segment}, {"_id": 0, "shopperId": 1, "segments": 1}
        ).limit(limit)
        results = list(cursor)
        return jsonify({"count": len(results), "results": results})
    except Exception:
        logger.exception("Error in list_by_segment")
        return jsonify({"success": False, "message": INTERNAL_ERROR}), 500


@app.route("/shoppers/<shopper_id>/events", methods=["POST"])
def track_event(shopper_id):
    """Record a view event and bump category affinity in ONE atomic update.

    Retry-safe: the caller supplies a unique `eventId`. The update filter excludes shoppers who
    already processed that eventId, so a replayed event is not counted twice. In that case the
    upsert tries to insert a second profile, hits the unique `shopperId` index, and is reported
    as a duplicate.
    """
    data = _json_body() or {}
    event_id, sku, category = data.get("eventId"), data.get("sku"), data.get("category")
    if not isinstance(event_id, str) or not event_id:
        return jsonify({"success": False, "message": "eventId is required and must be a string"}), 400
    if not isinstance(sku, str) or not sku:
        return jsonify({"success": False, "message": "sku is required and must be a string"}), 400
    if category is not None and (not isinstance(category, str) or not CATEGORY_PATTERN.match(category)):
        return jsonify({"success": False, "message": "category must match [a-z0-9_-]{1,40}"}), 400
    try:
        update = {
            "$push": {
                "recentViews": {"$each": [sku], "$slice": -RECENT_VIEWS_MAX},
                "recentEventIds": {"$each": [event_id], "$slice": -RECENT_EVENT_IDS_MAX},
            },
            "$set": {"lastActiveAt": datetime.now(timezone.utc)},
        }
        if category:
            update["$inc"] = {f"affinities.{category}": 1}
        get_collection().update_one(
            {"shopperId": shopper_id, "recentEventIds": {"$ne": event_id}}, update, upsert=True
        )
        return jsonify({"success": True})
    except DuplicateKeyError:
        return jsonify({"success": True, "duplicate": True})
    except Exception:
        logger.exception("Error in track_event")
        return jsonify({"success": False, "message": INTERNAL_ERROR}), 500


@app.route("/shoppers/<shopper_id>/recommend", methods=["GET"])
def recommend(shopper_id):
    """Toy recommendation: the shopper's top affinity categories (sorted in application code).

    Not an ML model. In a real system this profile is a feature source for a recommendation
    service such as Amazon Personalize.
    """
    try:
        doc = get_collection().find_one({"shopperId": shopper_id}, {"_id": 0, "affinities": 1})
        if not doc:
            return jsonify({"success": False, "message": "Shopper not found"}), 404
        ranked = sorted(doc.get("affinities", {}).items(), key=lambda kv: kv[1], reverse=True)
        return jsonify({"shopperId": shopper_id, "top_categories": [c for c, _ in ranked[:3]]})
    except Exception:
        logger.exception("Error in recommend")
        return jsonify({"success": False, "message": INTERNAL_ERROR}), 500


# ---------------------------------------------------------------------------
# Sample data: hand-written anchor shoppers (seed_data.json) plus deterministic generated shoppers
# ---------------------------------------------------------------------------

_CATEGORIES = ["shoes", "outerwear", "electronics", "home", "beauty", "toys", "sports", "grocery", "books", "jewelry", "garden", "pets"]
_SEGMENTS = ["frequent", "new", "mobile", "vip", "lapsed", "deal_seeker"]
_BRANDS = ["Acme", "Volt", "Nimbus", "Orion", "Pioneer"]


def _generate_shoppers(count: int, first_number: int, rng: Random, now: datetime):
    for i in range(count):
        n = first_number + i
        yield {
            "shopperId": f"s-{n}",
            "recentViews": [f"sku-{rng.randint(1, 500)}" for _ in range(rng.randint(0, RECENT_VIEWS_MAX))],
            "cart": [{"sku": f"sku-{rng.randint(1, 500)}", "qty": rng.randint(1, 3)} for _ in range(rng.randint(0, 3))],
            "affinities": {c: rng.randint(1, 40) for c in rng.sample(_CATEGORIES, k=rng.randint(1, 5))},
            "preferences": {"size": rng.choice(["XS", "S", "M", "L", "XL"]), "brand": rng.choice(_BRANDS)},
            "segments": rng.sample(_SEGMENTS, k=rng.randint(1, 3)),
            # Active within the last 90 days, so the 180-day TTL index keeps them
            "lastActiveAt": now - timedelta(days=rng.randint(0, 90), seconds=rng.randint(0, 86399)),
        }


def seed_if_empty(collection):
    """Load the anchor shoppers, then generate more (fixed PRNG seed, so every run is identical)."""
    if collection.count_documents({}, limit=1) > 0:
        return
    now = datetime.now(timezone.utc)
    docs = []
    seed_path = os.path.join(os.path.dirname(__file__), "seed_data.json")
    if os.path.exists(seed_path):
        with open(seed_path, "r", encoding="utf-8") as f:
            docs = json.load(f)
    else:
        logger.warning("Seed file %s not found; generating shoppers only.", seed_path)
    for doc in docs:
        doc["lastActiveAt"] = now   # anchor profiles are "active now" so the TTL index keeps them
    docs.extend(_generate_shoppers(max(0, SEED_COUNT - len(docs)), 10000, Random(42), now))
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
