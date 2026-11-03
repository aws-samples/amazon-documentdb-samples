import os
import sys
import json
import time
import logging
from datetime import datetime, timezone
from random import Random

from pymongo import MongoClient, ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from flask import Flask, request, jsonify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

DB_NAME = "clinical_trial_protocol_store"
PROTOCOLS = "protocols"                  # current design of each protocol
VERSIONS = "protocol_versions"           # one snapshot per superseded version (amendment history)

PHASES = {"I", "I/II", "II", "II/III", "III", "IV"}
STATUSES = {
    "not_yet_recruiting", "recruiting", "active_not_recruiting",
    "completed", "suspended", "terminated", "withdrawn",
}
STRING_FIELDS = {"title", "phase", "therapeutic_area", "sponsor", "status"}
STRING_LIST_FIELDS = {"inclusion_criteria", "exclusion_criteria", "primary_endpoints", "secondary_endpoints"}
MAX_ARMS = 20       # bounds on the nested arrays keep each protocol document small
MAX_VISITS = 100

SEED_COUNT = int(os.environ.get("SEED_COUNT", "500"))   # total protocols after seeding (anchors + generated)
SEED_BATCH = 250

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
            appname="clinical-trial-protocol-store-sample",
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
    # Every per-protocol read/update
    db[PROTOCOLS].create_index("protocol_id", unique=True, name="idx_protocol_id_unique")
    # GET /protocols?therapeutic_area=&phase=&status=  (serves any left-to-right prefix of the three)
    db[PROTOCOLS].create_index(
        [("therapeutic_area", ASCENDING), ("phase", ASCENDING), ("status", ASCENDING)],
        name="idx_area_phase_status",
    )
    # GET /protocols?phase=
    db[PROTOCOLS].create_index("phase", name="idx_phase")
    # GET /protocols?status=
    db[PROTOCOLS].create_index("status", name="idx_status")
    # GET /protocols/<id>/versions  (also guarantees one snapshot per version)
    db[VERSIONS].create_index(
        [("protocol_id", ASCENDING), ("version", DESCENDING)], unique=True, name="idx_protocol_version"
    )
    logger.info("Indexes ensured.")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

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


def _is_str(v):
    return isinstance(v, str) and v != ""


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _arm_error(arm):
    """Return an error message for an invalid treatment arm, or None if it is valid."""
    if not isinstance(arm, dict) or set(arm) != {"arm_name", "intervention", "dosing_schedule"}:
        return "arm must have exactly: arm_name, intervention, dosing_schedule"
    if not all(_is_str(v) for v in arm.values()):
        return "arm fields must be non-empty strings"
    return None


def _visit_error(visit):
    """Return an error message for an invalid visit definition, or None if it is valid."""
    if not isinstance(visit, dict) or set(visit) != {"visit_name", "study_day", "window_days", "procedures"}:
        return "visit must have exactly: visit_name, study_day, window_days, procedures"
    if not _is_str(visit["visit_name"]) or not _is_int(visit["study_day"]):
        return "visit_name must be a string and study_day an integer"
    if not _is_int(visit["window_days"]) or visit["window_days"] < 0:
        return "window_days must be an integer >= 0"
    if not isinstance(visit["procedures"], list) or not all(_is_str(p) for p in visit["procedures"]):
        return "procedures must be a list of strings"
    return None


def _protocol_fields_error(data: dict):
    """Allowlist and validate the design fields a caller may write.

    Returns an error message, or None if the fields are valid.
    """
    allowed = STRING_FIELDS | STRING_LIST_FIELDS | {"treatment_arms", "visit_schedule"}
    unknown = set(data) - allowed
    if unknown:
        return f"Fields not writable: {sorted(unknown)}"
    for f in STRING_FIELDS & set(data):
        if not _is_str(data[f]):
            return f"{f} must be a non-empty string"
    if "phase" in data and data["phase"] not in PHASES:
        return f"phase must be one of {sorted(PHASES)}"
    if "status" in data and data["status"] not in STATUSES:
        return f"status must be one of {sorted(STATUSES)}"
    for f in STRING_LIST_FIELDS & set(data):
        if not isinstance(data[f], list) or not all(_is_str(x) for x in data[f]):
            return f"{f} must be a list of strings"
    if "treatment_arms" in data:
        arms = data["treatment_arms"]
        if not isinstance(arms, list) or len(arms) > MAX_ARMS:
            return f"treatment_arms must be a list of at most {MAX_ARMS}"
        for a in arms:
            error = _arm_error(a)
            if error:
                return error
    if "visit_schedule" in data:
        visits = data["visit_schedule"]
        if not isinstance(visits, list) or len(visits) > MAX_VISITS:
            return f"visit_schedule must be a list of at most {MAX_VISITS}"
        for v in visits:
            error = _visit_error(v)
            if error:
                return error
    return None


# ---------------------------------------------------------------------------
# Amendment tracking
# ---------------------------------------------------------------------------

def _amend(db, flt: dict, update: dict, upsert: bool = False):
    """Apply an update to a protocol atomically, bump its version, and archive the previous state.

    `find_one_and_update` returns the document as it was BEFORE the change, in the same atomic
    operation, so concurrent amendments each archive a distinct prior version. Returns None when
    nothing matched (or, with upsert, when the protocol was just created).
    """
    now = datetime.now(timezone.utc)
    update.setdefault("$set", {})["updatedAt"] = now
    update.setdefault("$inc", {})["version"] = 1
    before = db[PROTOCOLS].find_one_and_update(
        flt, update, upsert=upsert, return_document=ReturnDocument.BEFORE
    )
    if before is not None:
        snapshot = {k: v for k, v in before.items() if k != "_id"}
        db[VERSIONS].insert_one({
            "protocol_id": before["protocol_id"],
            "version": before.get("version", 1),
            "snapshot": snapshot,
            "archivedAt": now,
        })
    return before


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/protocols/<protocol_id>", methods=["PUT"])
def upsert_protocol(protocol_id):
    """Create or update a protocol's design metadata. Each update is a new version."""
    data = _json_body()
    if data is None:
        return jsonify({"success": False, "message": "Request body must be a JSON object"}), 400
    error = _protocol_fields_error(data)
    if error:
        return jsonify({"success": False, "message": f"Invalid input: {error}"}), 400
    try:
        before = _amend(get_db(), {"protocol_id": protocol_id}, {"$set": dict(data)}, upsert=True)
        return jsonify({"success": True, "created": before is None})
    except Exception:
        logger.exception("Error in upsert_protocol")
        return jsonify({"success": False, "message": INTERNAL_ERROR}), 500


@app.route("/protocols/<protocol_id>", methods=["GET"])
def get_protocol(protocol_id):
    """Return a single protocol's current design metadata."""
    try:
        doc = get_db()[PROTOCOLS].find_one({"protocol_id": protocol_id}, {"_id": 0})
        if not doc:
            return jsonify({"success": False, "message": "Protocol not found"}), 404
        doc["visit_schedule"] = sorted(doc.get("visit_schedule", []), key=lambda v: v["study_day"])
        return jsonify(doc)
    except Exception:
        logger.exception("Error in get_protocol")
        return jsonify({"success": False, "message": INTERNAL_ERROR}), 500


@app.route("/protocols/<protocol_id>/versions", methods=["GET"])
def get_versions(protocol_id):
    """Amendment history, newest first (bounded to 50)."""
    limit, error = _parse_limit(10, 50)
    if error:
        return jsonify({"success": False, "message": f"Invalid input: {error}"}), 400
    try:
        cursor = (
            get_db()[VERSIONS]
            .find({"protocol_id": protocol_id}, {"_id": 0})
            .sort("version", DESCENDING)
            .limit(limit)
        )
        return jsonify({"results": list(cursor)})
    except Exception:
        logger.exception("Error in get_versions")
        return jsonify({"success": False, "message": INTERNAL_ERROR}), 500


@app.route("/protocols", methods=["GET"])
def search_protocols():
    """Search by allowlisted exact-match filters. Bounded (max 100) and paged with ?after=<protocol_id>."""
    limit, error = _parse_limit(25, 100)
    if error:
        return jsonify({"success": False, "message": f"Invalid input: {error}"}), 400
    try:
        query = {}
        for field in ("therapeutic_area", "phase", "status"):
            if field in request.args:
                query[field] = request.args[field]
        if "after" in request.args:
            query["protocol_id"] = {"$gt": request.args["after"]}
        projection = {"_id": 0, "protocol_id": 1, "title": 1, "phase": 1, "therapeutic_area": 1, "status": 1}
        results = list(get_db()[PROTOCOLS].find(query, projection).sort("protocol_id", ASCENDING).limit(limit))
        return jsonify({"count": len(results), "results": results})
    except Exception:
        logger.exception("Error in search_protocols")
        return jsonify({"success": False, "message": INTERNAL_ERROR}), 500


def _add_nested(protocol_id, array_field, name_field, item, max_items):
    """Append to a nested array only if an entry with the same name is absent and the cap is not reached.

    Both conditions are part of the update filter, so the append is atomic, retry-safe (a repeat
    is rejected, not duplicated), and bounded.
    """
    db = get_db()
    flt = {
        "protocol_id": protocol_id,
        f"{array_field}.{name_field}": {"$ne": item[name_field]},
        f"{array_field}.{max_items - 1}": {"$exists": False},
    }
    before = _amend(db, flt, {"$push": {array_field: item}})
    if before is not None:
        return jsonify({"success": True})
    if db[PROTOCOLS].count_documents({"protocol_id": protocol_id}, limit=1) == 0:
        return jsonify({"success": False, "message": "Protocol not found"}), 404
    return jsonify({"success": False, "message": "Duplicate name or array is full"}), 409


@app.route("/protocols/<protocol_id>/arms", methods=["POST"])
def add_treatment_arm(protocol_id):
    """Add a treatment arm (amendment)."""
    arm = _json_body()
    error = _arm_error(arm)
    if error:
        return jsonify({"success": False, "message": f"Invalid input: {error}"}), 400
    try:
        return _add_nested(protocol_id, "treatment_arms", "arm_name", arm, MAX_ARMS)
    except Exception:
        logger.exception("Error in add_treatment_arm")
        return jsonify({"success": False, "message": INTERNAL_ERROR}), 500


@app.route("/protocols/<protocol_id>/visits", methods=["POST"])
def add_visit(protocol_id):
    """Add a visit definition (amendment)."""
    visit = _json_body()
    error = _visit_error(visit)
    if error:
        return jsonify({"success": False, "message": f"Invalid input: {error}"}), 400
    try:
        return _add_nested(protocol_id, "visit_schedule", "visit_name", visit, MAX_VISITS)
    except Exception:
        logger.exception("Error in add_visit")
        return jsonify({"success": False, "message": INTERNAL_ERROR}), 500


# ---------------------------------------------------------------------------
# Sample data: hand-written anchor protocols (seed_data.json) plus deterministic generated protocols
# ---------------------------------------------------------------------------

_AREAS = {
    "respiratory": ["moderate persistent asthma", "chronic obstructive pulmonary disease"],
    "oncology": ["stage III non-small cell lung cancer", "metastatic colorectal cancer"],
    "immunology": ["rheumatoid arthritis", "plaque psoriasis"],
    "cardiology": ["heart failure with reduced ejection fraction", "resistant hypertension"],
    "neurology": ["relapsing multiple sclerosis", "migraine prevention"],
    "infectious_disease": ["community-acquired pneumonia", "complicated urinary tract infection"],
    "endocrinology": ["type 2 diabetes", "obesity"],
    "dermatology": ["atopic dermatitis", "alopecia areata"],
}
_VISITS = [("Screening", -14), ("Baseline", 0), ("Week 2", 14), ("Week 4", 28), ("Week 8", 56),
           ("Week 12", 84), ("Follow-up", 112), ("End of study", 140)]
_PROCEDURES = ["informed consent", "vital signs", "blood draw", "ECG", "physical exam", "questionnaire", "imaging", "urinalysis"]
_INCLUSION = ["Age 18-75 years", "Confirmed diagnosis at screening", "Able to provide informed consent", "Stable concomitant therapy for 4 weeks"]
_EXCLUSION = ["Pregnant or breastfeeding", "Participation in another interventional trial within 30 days", "Known hypersensitivity to study drug", "Active infection at screening"]
_ENDPOINTS = ["Change from baseline at week 12", "Time to first event", "Proportion of responders at week 24", "Change in patient-reported score"]


def _generate_protocols(count: int, first_number: int, rng: Random):
    for i in range(count):
        n = first_number + i
        area = rng.choice(list(_AREAS))
        phase = rng.choices(["I", "I/II", "II", "II/III", "III", "IV"], weights=[15, 5, 35, 5, 35, 5])[0]
        code = f"EX-{rng.randint(100, 999)}"
        arm_count = rng.randint(2, 4)
        yield {
            "protocol_id": f"ct-{n}",
            "title": f"A Phase {phase} Study of Compound {code} in {rng.choice(_AREAS[area])}",
            "phase": phase,
            "therapeutic_area": area,
            "sponsor": f"Example Sponsor {rng.randint(1, 25)}",
            "status": rng.choices(
                ["not_yet_recruiting", "recruiting", "active_not_recruiting", "completed", "suspended", "terminated", "withdrawn"],
                weights=[8, 30, 25, 30, 3, 3, 1],
            )[0],
            "treatment_arms": [
                {
                    "arm_name": "Arm A - Placebo" if j == 0 else f"Arm {chr(65 + j)} - {code} {50 * j}mg",
                    "intervention": "Placebo" if j == 0 else f"{code} {50 * j}mg",
                    "dosing_schedule": "Once daily, oral, 12 weeks",
                }
                for j in range(arm_count)
            ],
            "visit_schedule": [
                {"visit_name": name, "study_day": day, "window_days": rng.choice([1, 2, 3, 7]),
                 "procedures": rng.sample(_PROCEDURES, k=rng.randint(1, 4))}
                for name, day in _VISITS[: rng.randint(3, len(_VISITS))]
            ],
            "inclusion_criteria": rng.sample(_INCLUSION, k=rng.randint(2, 4)),
            "exclusion_criteria": rng.sample(_EXCLUSION, k=rng.randint(2, 4)),
            "primary_endpoints": rng.sample(_ENDPOINTS, k=1),
            "secondary_endpoints": rng.sample(_ENDPOINTS, k=rng.randint(1, 3)),
        }


def seed_if_empty(db):
    """Load the anchor protocols, then generate more (fixed PRNG seed, so every run is identical)."""
    if db[PROTOCOLS].count_documents({}, limit=1) > 0:
        return
    docs = []
    seed_path = os.path.join(os.path.dirname(__file__), "seed_data.json")
    if os.path.exists(seed_path):
        with open(seed_path, "r", encoding="utf-8") as f:
            docs = json.load(f)
    else:
        logger.warning("Seed file %s not found; generating protocols only.", seed_path)
    docs.extend(_generate_protocols(max(0, SEED_COUNT - len(docs)), 3000, Random(42)))
    now = datetime.now(timezone.utc)
    for doc in docs:
        doc["version"] = 1
        doc["updatedAt"] = now
    for i in range(0, len(docs), SEED_BATCH):
        db[PROTOCOLS].insert_many(docs[i:i + SEED_BATCH], ordered=False)
    logger.info("Inserted %d sample protocols", len(docs))


def cleanup():
    """Drop every collection this sample created."""
    db = get_db()
    for name in (PROTOCOLS, VERSIONS):
        db.drop_collection(name)
    logger.info("Dropped collections: %s, %s", PROTOCOLS, VERSIONS)


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
