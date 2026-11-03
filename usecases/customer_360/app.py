import os
import sys
import json
import time
import logging
from urllib.parse import parse_qs
from datetime import datetime, timedelta, timezone
from random import Random

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from flask import Flask, request, jsonify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

DB_NAME = "customer_360_store"
PROFILES = "customers"                 # one document per customer (the "360" read model)
HISTORY = "customer_interactions"      # full interaction history, one document per event

# Number of recent interactions kept inside the profile document. The full history
# lives in the HISTORY collection so the profile document can never grow without bound.
RECENT_INTERACTIONS_MAX = 50

# Fields a caller may write through PUT /customers/<id>.
# `kyc` is deliberately NOT here: KYC state is owned by the KYC system of record and
# should be synced by a trusted back-end process, never set by an arbitrary caller.
WRITABLE_PROFILE_FIELDS = {"displayName", "accounts", "preferences", "segments"}

# Fields a caller may request through GET /customers/<id>?fields=. `kyc` is excluded: it is a
# regulated attribute, so a channel projection cannot ask for it by name.
PROJECTABLE_FIELDS = {"customerId", "displayName", "accounts", "preferences", "segments",
                      "recentInteractions", "updatedAt"}

# Bounds for PUT /customers/<id> values
MAX_STR_LEN = 100
MAX_SEGMENTS = 20
MAX_ACCOUNTS = 20
MAX_PREFERENCES = 20

SEED_COUNT = int(os.environ.get("SEED_COUNT", "1000"))   # total customers after seeding (anchors + generated)
SEED_BATCH = 500

_client = None


# Returned for unexpected server errors; details go to the server log only.
INTERNAL_ERROR = "An internal error occurred. Check the server logs for details."


def get_config() -> dict:
    """Read the cluster connection string and refuse to start without TLS and a CA bundle.

    The URI must contain tls=true (or ssl=true) and a tlsCAFile, or DOCDB_TLS_CA must name the
    CA bundle. Exits with a logged error otherwise.
    """
    uri = os.environ.get("DOCDB_URI")
    if not uri:
        logger.error("Missing required environment variable DOCDB_URI. See README.md for the expected format.")
        sys.exit(1)
    params = {k.lower(): v for k, v in parse_qs(uri.partition("?")[2]).items()}
    tls_values = [x.lower() for x in params.get("tls", []) + params.get("ssl", [])]
    if not tls_values or any(v != "true" for v in tls_values):
        logger.error("DOCDB_URI must enable TLS (tls=true) and must not disable it. See README.md.")
        sys.exit(1)
    insecure = params.get("tlsallowinvalidcertificates", []) + params.get("tlsinsecure", [])
    if any(v.lower() == "true" for v in insecure):
        logger.error("DOCDB_URI must not disable certificate validation.")
        sys.exit(1)
    ca_in_uri = any(params.get("tlscafile", []))
    ca_from_env = os.environ.get("DOCDB_TLS_CA")
    if not ca_in_uri and not ca_from_env:
        logger.error("A CA bundle is required: add tlsCAFile=<path> to DOCDB_URI or set DOCDB_TLS_CA. See README.md.")
        sys.exit(1)
    return {"uri": uri, "tls_ca_file": None if ca_in_uri else ca_from_env}


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
    if "displayName" in data and not _is_short_str(data["displayName"]):
        return f"displayName must be a non-empty string of at most {MAX_STR_LEN} characters"
    if "segments" in data:
        seg = data["segments"]
        if not isinstance(seg, list) or len(seg) > MAX_SEGMENTS or not all(_is_short_str(x, 40) for x in seg):
            return f"segments must be a list of at most {MAX_SEGMENTS} strings (1-40 characters)"
    if "accounts" in data:
        acc = data["accounts"]
        if (not isinstance(acc, list) or len(acc) > MAX_ACCOUNTS or not all(
                isinstance(a, dict) and set(a) == {"type", "id"}
                and _is_short_str(a["type"], 40) and _is_short_str(a["id"], 60) for a in acc)):
            return f"accounts must be a list of at most {MAX_ACCOUNTS} objects with string type and id"
    if "preferences" in data:
        pref = data["preferences"]
        if (not isinstance(pref, dict) or len(pref) > MAX_PREFERENCES or not all(
                _is_short_str(k, 40) and not k.startswith("$") and "." not in k
                and (isinstance(v, (int, float, bool)) or (isinstance(v, str) and len(v) <= MAX_STR_LEN))
                for k, v in pref.items())):
            return (
                f"preferences must be an object of at most {MAX_PREFERENCES} scalar values "
                f"(strings up to {MAX_STR_LEN} characters)")
    return None


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
            **({"tlsCAFile": config["tls_ca_file"]} if config["tls_ca_file"] else {}),
            retryWrites=False,
            appname="customer-360-store-sample",
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


def get_db():
    return get_client()[DB_NAME]


def ensure_indexes(db) -> None:
    """Create indexes once at startup. Each index backs a query issued below."""
    # GET/PUT /customers/<id>
    db[PROFILES].create_index("customerId", unique=True, name="idx_customerId_unique")
    # GET /customers?segment=<name>
    db[PROFILES].create_index("segments", name="idx_segments")
    # GET /customers/<id>/interactions (newest first)
    # (_id breaks ties between events recorded in the same millisecond)
    db[HISTORY].create_index(
        [("customerId", ASCENDING), ("ts", DESCENDING), ("_id", DESCENDING)], name="idx_customer_ts"
    )
    logger.info("Indexes ensured.")


def _json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


@app.route("/customers/<customer_id>", methods=["PUT"])
def upsert_customer(customer_id):
    """Create or update the profile. Only allowlisted fields are written (never `kyc`)."""
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
        update = {
            "$setOnInsert": {"customerId": customer_id, "recentInteractions": []},
            "$set": {**data, "updatedAt": datetime.now(timezone.utc)},
        }
        get_db()[PROFILES].update_one({"customerId": customer_id}, update, upsert=True)
        return jsonify({"success": True})
    except Exception:
        logger.exception("Error in upsert_customer")
        return jsonify({"success": False, "message": INTERNAL_ERROR}), 500


@app.route("/customers/<customer_id>", methods=["GET"])
def get_customer(customer_id):
    """Return the unified profile. Use ?fields=a,b to project only what a channel needs."""
    projection = {"_id": 0}
    fields = request.args.get("fields")
    if fields:
        names = [f.strip() for f in fields.split(",")]
        bad = sorted({n for n in names if n not in PROJECTABLE_FIELDS})
        if bad:
            return jsonify({"success": False,
                            "message": f"Unknown fields: {bad}. Allowed: {sorted(PROJECTABLE_FIELDS)}"}), 400
        projection.update({n: 1 for n in names})
    try:
        doc = get_db()[PROFILES].find_one({"customerId": customer_id}, projection)
        if not doc:
            return jsonify({"success": False, "message": "Customer not found"}), 404
        return jsonify(doc)
    except Exception:
        logger.exception("Error in get_customer")
        return jsonify({"success": False, "message": INTERNAL_ERROR}), 500


@app.route("/customers", methods=["GET"])
def list_by_segment():
    """List customers in a segment (bounded to 100, minimal projection)."""
    segment = request.args.get("segment")
    if not segment:
        return jsonify({"success": False, "message": "segment query parameter is required"}), 400
    limit, error = _parse_limit(25, 100)
    if error:
        return jsonify({"success": False, "message": f"Invalid input: {error}"}), 400
    try:
        cursor = get_db()[PROFILES].find(
            {"segments": segment},
            {"_id": 0, "customerId": 1, "displayName": 1, "segments": 1},
        ).limit(limit)
        results = list(cursor)
        return jsonify({"count": len(results), "results": results})
    except Exception:
        logger.exception("Error in list_by_segment")
        return jsonify({"success": False, "message": INTERNAL_ERROR}), 500


@app.route("/customers/<customer_id>/interactions", methods=["POST"])
def add_interaction(customer_id):
    """Record an interaction.

    1. Insert the event into the history collection (unbounded, indexed, one doc per event).
    2. Push it onto the profile's `recentInteractions` array, capped with $slice.
    """
    event = _json_body()
    if not event or not isinstance(event.get("channel"), str) or not isinstance(event.get("action"), str):
        return jsonify({"success": False, "message": "channel and action are required strings"}), 400
    try:
        db = get_db()
        if db[PROFILES].count_documents({"customerId": customer_id}, limit=1) == 0:
            return jsonify({"success": False, "message": "Customer not found"}), 404
        entry = {
            "channel": event["channel"],
            "action": event["action"],
            "ts": datetime.now(timezone.utc),
        }
        db[HISTORY].insert_one({"customerId": customer_id, **entry})
        db[PROFILES].update_one(
            {"customerId": customer_id},
            {"$push": {"recentInteractions": {"$each": [entry], "$slice": -RECENT_INTERACTIONS_MAX}}},
        )
        return jsonify({"success": True})
    except Exception:
        logger.exception("Error in add_interaction")
        return jsonify({"success": False, "message": INTERNAL_ERROR}), 500


@app.route("/customers/<customer_id>/interactions", methods=["GET"])
def get_interactions(customer_id):
    """Page through full interaction history, newest first (bounded to 200)."""
    limit, error = _parse_limit(50, 200)
    if error:
        return jsonify({"success": False, "message": f"Invalid input: {error}"}), 400
    try:
        cursor = (
            get_db()[HISTORY]
            .find({"customerId": customer_id}, {"_id": 0})
            .sort([("ts", DESCENDING), ("_id", DESCENDING)])
            .limit(limit)
        )
        results = list(cursor)
        return jsonify({"count": len(results), "results": results})
    except Exception:
        logger.exception("Error in get_interactions")
        return jsonify({"success": False, "message": INTERNAL_ERROR}), 500


def _parse_seed_dates(doc):
    for event in doc.get("recentInteractions", []):
        if isinstance(event.get("ts"), str):
            event["ts"] = datetime.fromisoformat(event["ts"]).replace(tzinfo=timezone.utc)
    return doc


# ---------------------------------------------------------------------------
# Sample data: hand-written anchor customers (seed_data.json) plus deterministic generated customers
# ---------------------------------------------------------------------------

_SEGMENTS = ["wealth", "mobile_first", "retail", "small_business", "student", "premium"]
_ACCOUNT_TYPES = ["checking", "savings", "credit", "mortgage", "investment"]
_CHANNELS = ["app", "web", "branch", "call_center", "atm"]
_ACTIONS = ["login", "view_statement", "transfer", "card_freeze", "update_address", "open_account", "support_call"]


def _generate_customers(count: int, first_number: int, rng: Random, now: datetime):
    """Yield (profile, history_events) pairs. 0-30 interactions per customer, spread over a year."""
    for i in range(count):
        n = first_number + i
        cid = f"c-{n}"
        stamps = sorted(now - timedelta(seconds=rng.randint(0, 365 * 86400)) for _ in range(rng.randint(0, 30)))
        events = [{"channel": rng.choice(_CHANNELS), "action": rng.choice(_ACTIONS), "ts": ts} for ts in stamps]
        profile = {
            "customerId": cid,
            "displayName": f"Sample Customer {n}",
            "accounts": [
                {"type": t, "id": f"{t[:3]}-{n}-{j}"}
                for j, t in enumerate(rng.sample(_ACCOUNT_TYPES, k=rng.randint(1, 4)))
            ],
            "recentInteractions": events[-RECENT_INTERACTIONS_MAX:],
            "preferences": {"channel": rng.choice(_CHANNELS[:3]), "language": rng.choice(["en", "es", "fr"])},
            "segments": rng.sample(_SEGMENTS, k=rng.randint(1, 3)),
            "kyc": {"status": rng.choices(["verified", "pending", "expired"], weights=[85, 10, 5])[0],
                    "level": rng.randint(1, 3)},
            "updatedAt": now,
        }
        yield profile, [{"customerId": cid, **e} for e in events]


def _insert_batched(collection, docs):
    for i in range(0, len(docs), SEED_BATCH):
        collection.insert_many(docs[i:i + SEED_BATCH], ordered=False)


def seed_if_empty(db):
    """Load the anchor customers, then generate more (fixed PRNG seed, so every run is identical)."""
    if db[PROFILES].count_documents({}, limit=1) > 0:
        return
    now = datetime.now(timezone.utc)
    profiles, history = [], []
    seed_path = os.path.join(os.path.dirname(__file__), "seed_data.json")
    if os.path.exists(seed_path):
        with open(seed_path, "r", encoding="utf-8") as f:
            profiles = [_parse_seed_dates(d) for d in json.load(f)]
        history = [{"customerId": d["customerId"], **e} for d in profiles for e in d.get("recentInteractions", [])]
    else:
        logger.warning("Seed file %s not found; generating customers only.", seed_path)
    for profile, events in _generate_customers(max(0, SEED_COUNT - len(profiles)), 10000, Random(42), now):
        profiles.append(profile)
        history.extend(events)
    _insert_batched(db[PROFILES], profiles)
    _insert_batched(db[HISTORY], history)
    logger.info("Inserted %d sample customers and %d interactions", len(profiles), len(history))


def cleanup():
    """Drop every collection this sample created."""
    db = get_db()
    for name in (PROFILES, HISTORY):
        db.drop_collection(name)
    logger.info("Dropped collections: %s, %s", PROFILES, HISTORY)


if __name__ == "__main__":
    try:
        if "--cleanup" in sys.argv:
            cleanup()
            sys.exit(0)
        db = get_db()
        ensure_indexes(db)
        seed_if_empty(db)
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
