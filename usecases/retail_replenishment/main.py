"""Retail replenishment pattern detection with Amazon DocumentDB.

Use case
--------
Retailers selling consumables (pet food, vitamins, coffee, contact lenses)
depend on repeat purchases. Customers run out on a fairly predictable cadence,
but most storefronts only react *after* a reorder instead of predicting it.
This sample mines order history to answer two questions:

1. Which ``(customer, SKU)`` pairs are bought on a recurring cadence, and how
   reliable is that cadence?
2. Which customers are due - or overdue - for a reorder right now?

What it demonstrates
--------------------
* A **server-side aggregation pipeline** with ``$match`` as the first stage so
  DocumentDB can use an index, avoiding a full collection scan.
* **Incremental processing** - only orders since the last run are scanned,
  with new intervals merged into running statistics on each pattern document.
* **Batched bulk writes** that flush every N operations, preventing unbounded
  memory growth
* **Idempotent writes** via deterministic ``_id`` values, so re-running the
  pipeline replaces results instead of duplicating them.
* **Stale recommendation cleanup** - patterns that drop below the confidence
  threshold have their recommendations purged automatically.
* **Indexes created once at startup**, each matching a query this code issues.
* **TLS with CA validation** and credentials sourced from the environment.

Point it at your cluster
------------------------
Set the ``DOCDB_URI`` environment variable to your cluster's connection string:

    export DOCDB_URI="mongodb://<user>:<pass>@your-cluster.cluster-xxx.us-east-1.docdb.amazonaws.com:27017/?tls=true&tlsCAFile=global-bundle.pem&retryWrites=false&readPreference=secondaryPreferred"

Optional: ``DOCDB_DATABASE`` ("replenishment"), ``CONFIDENCE_THRESHOLD`` (0.4).

Run it
------
    python main.py

The script is safe to re-run: each run starts fresh with clean data.
Use ``--cleanup`` when finished to remove all sample collections.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import date, datetime, time as dtime, timedelta, timezone
from math import sqrt
from random import Random
from typing import Any, Dict, List, Sequence, Tuple

import pymongo
from pymongo import UpdateOne

# ---------------------------------------------------------------------------
# Tunables
#
# Kept as module constants rather than environment variables to keep the
# sample's configuration surface small. Adjust them here if you want to see
# how the classification shifts.
# ---------------------------------------------------------------------------

#: A pattern needs at least this many purchases before it is trustworthy.
MIN_OBSERVATIONS = 3

#: Days before the expected reorder date that count as "due now".
DUE_NOW_WINDOW_DAYS = 3

#: Days past the expected reorder date still treated as "due now" rather
#: than "overdue".
OVERDUE_GRACE_DAYS = 2

#: Maximum age of orders to consider during a full rebuild. Orders older than
#: this contribute negligible signal - a purchase from years ago doesn't help
#: predict when someone will reorder next month.
DETECTION_WINDOW_DAYS = 365

#: Number of UpdateOne operations to accumulate before flushing to DocumentDB.
#: Keeps memory bounded and stays within the 16 MB wire-protocol message limit.
BULK_BATCH_SIZE = 1000

#: Sent to DocumentDB on every connection; makes this sample's traffic easy
#: to spot in server logs and CloudWatch.
APPNAME = "retail-replenishment-sample"

#: Ranking order for the report: overdue first, then due now, then upcoming.
URGENCY_RANK = {"overdue": 0, "due_now": 1, "upcoming": 2}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("replenishment")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def load_config() -> Dict[str, Any]:
    """Read connection settings from the environment."""
    uri = os.environ.get("DOCDB_URI")
    if not uri:
        log.error(
            "Missing required environment variable DOCDB_URI. "
            "See README.md for the expected connection string format.",
        )
        sys.exit(2)

    return {
        "uri": uri,
        "database": os.environ.get("DOCDB_DATABASE", "replenishment"),
        "confidence_threshold": float(os.environ.get("CONFIDENCE_THRESHOLD", "0.4")),
    }


def connect(config: Dict[str, Any]) -> pymongo.MongoClient:
    """Open a single verified connection to Amazon DocumentDB."""
    try:
        client = pymongo.MongoClient(
            config["uri"],
            serverSelectionTimeoutMS=5000,
            maxPoolSize=20,
            minPoolSize=1,
            appname=APPNAME,
        )
        client.admin.command("ping")
    except Exception as exc:
        log.error("Failed to connect to DocumentDB: %s", exc)
        sys.exit(1)

    log.info("Connected to Amazon DocumentDB (database=%s)", config["database"])
    return client


def ensure_indexes(db) -> None:
    """Create the indexes this sample queries against, once at startup.

    Creating indexes inside request or loop bodies adds latency to every
    operation and races concurrent builds. Each ``create_index`` call is
    idempotent, so re-runs are no-ops.

    Every index below backs a query this script actually issues:

    * the three unique keys make the seeder's upserts idempotent
    * ``order_date_asc`` supports the aggregation pipeline's $match first stage
    * ``confidence`` backs the recommender's threshold scan
    * the compound urgency index backs the sorted read in the report
    """
    db.customers.create_index("customer_id", unique=True, name="customer_id_unique")
    db.products.create_index("sku", unique=True, name="sku_unique")
    db.orders.create_index("order_id", unique=True, name="order_id_unique")
    db.orders.create_index([("order_date", 1)], name="order_date_asc")
    db.purchase_patterns.create_index([("confidence", -1)], name="confidence_desc")
    db.reorder_recommendations.create_index(
        [("urgency_status", 1), ("next_expected_reorder_date", 1)],
        name="urgency_next_date",
    )
    log.info("Indexes ready")


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

_NUM_CUSTOMERS = 12
_NUM_PRODUCTS = 18
_HISTORY_DAYS = 200

#: Realistic replenishment cadences, in days.
_INTERVALS: Sequence[int] = (14, 21, 28, 30, 60)

_CUSTOMER_NAMES: Sequence[str] = (
    "Alex Rivera", "Blake Chen", "Casey Kim", "Drew Patel",
    "Evan Garcia", "Finley Okafor", "Gray Nakamura", "Harper Singh",
    "Indigo Thompson", "Jordan Alvarez", "Kai Robinson", "Logan Mitchell",
)

_PRODUCTS: Sequence[Dict[str, Any]] = (
    {"name": "Premium Dog Food, 12 lb", "category": "pet-food", "unit_price": 42.99},
    {"name": "Cat Litter, 20 lb", "category": "pet-food", "unit_price": 18.49},
    {"name": "Dog Treats Variety Pack", "category": "pet-food", "unit_price": 14.99},
    {"name": "Cat Food, 7 lb", "category": "pet-food", "unit_price": 24.99},
    {"name": "Multivitamin, 60 ct", "category": "supplements", "unit_price": 19.99},
    {"name": "Fish Oil, 120 ct", "category": "supplements", "unit_price": 24.95},
    {"name": "Probiotic Capsules, 30 ct", "category": "supplements", "unit_price": 29.99},
    {"name": "Vitamin C, 100 ct", "category": "supplements", "unit_price": 13.99},
    {"name": "Laundry Detergent, 96 oz", "category": "cleaning", "unit_price": 15.99},
    {"name": "Dish Soap, 28 oz", "category": "cleaning", "unit_price": 4.49},
    {"name": "All-Purpose Cleaner, 32 oz", "category": "cleaning", "unit_price": 5.99},
    {"name": "Paper Towels, 12 rolls", "category": "cleaning", "unit_price": 22.99},
    {"name": "Coffee Beans, 2 lb", "category": "groceries", "unit_price": 19.99},
    {"name": "Olive Oil, 1 L", "category": "groceries", "unit_price": 12.99},
    {"name": "Breakfast Cereal, 18 oz", "category": "groceries", "unit_price": 5.49},
    {"name": "Toothpaste, 6 oz", "category": "personal-care", "unit_price": 4.99},
    {"name": "Shampoo, 16 oz", "category": "personal-care", "unit_price": 8.99},
    {"name": "Razor Cartridges, 8 ct", "category": "personal-care", "unit_price": 27.99},
)


def seed_sample_data(db) -> None:
    """Populate ``customers``, ``products``, and ``orders``.

    Generation is seeded with a fixed PRNG so every run produces identical
    data. Each customer gets 2-4 recurring products purchased at a base
    interval with a day of jitter - enough signal for the detector to find a
    stable cadence - plus a few one-off orders that fall below
    ``MIN_OBSERVATIONS`` and are correctly ignored.
    """
    rng = Random(42)
    now = datetime.now(timezone.utc)
    today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    start = today - timedelta(days=_HISTORY_DAYS)

    customers = []
    for i in range(_NUM_CUSTOMERS):
        name = _CUSTOMER_NAMES[i % len(_CUSTOMER_NAMES)]
        customer_id = f"CUST-{i + 1:04d}"
        customers.append(
            {
                "customer_id": customer_id,
                "name": name,
                "email": f"{name.split()[0].lower()}.{customer_id.lower()}@example.com",
                "created_at": today - timedelta(days=rng.randint(30, 730)),
            }
        )

    products = []
    for i in range(_NUM_PRODUCTS):
        entry = _PRODUCTS[i % len(_PRODUCTS)]
        products.append(
            {
                "sku": f"SKU-{entry['category'].upper().replace('-', '')}-{i + 1:03d}",
                "name": entry["name"],
                "category": entry["category"],
                "unit_price": entry["unit_price"],
                "typical_reorder_days": rng.choice(_INTERVALS),
            }
        )

    orders: List[Dict[str, Any]] = []
    for customer in customers:
        # Recurring purchases: the signal the detector is built to find.
        for product in rng.sample(products, k=rng.randint(2, 4)):
            interval = rng.choice(_INTERVALS)
            # Roughly a third of these series stop before today. Those are the
            # customers quietly drifting away, and they are exactly what the
            # report flags as "overdue" - the ones worth reaching out to.
            lapsed = rng.randint(1, 3) == 1
            series_end = (
                today - timedelta(days=int(interval * rng.uniform(1.2, 2.5)))
                if lapsed
                else today
            )
            t = start + timedelta(days=rng.randint(0, interval))
            while t <= series_end:
                orders.append(_make_order(customer, product, t, products, rng))
                # A day of jitter keeps the interval realistic while leaving
                # the standard deviation low enough to score well.
                t += timedelta(days=interval + rng.randint(-1, 1))

        # One-off purchases: noise that should not become a pattern.
        for _ in range(rng.randint(1, 3)):
            t = start + timedelta(days=rng.randint(0, _HISTORY_DAYS))
            orders.append(
                _make_order(customer, rng.choice(products), t, products, rng)
            )

    # Assign order ids after generation so they are unique and stable.
    for i, order in enumerate(orders, start=1):
        order["order_id"] = f"ORD-{i:06d}"

    _upsert(db.customers, customers, "customer_id")
    _upsert(db.products, products, "sku")
    _upsert(db.orders, orders, "order_id")
    log.info(
        "Seeded customers=%d products=%d orders=%d",
        len(customers),
        len(products),
        len(orders),
    )


def _make_order(
    customer: Dict[str, Any],
    product: Dict[str, Any],
    order_date: datetime,
    catalog: Sequence[Dict[str, Any]],
    rng: Random,
) -> Dict[str, Any]:
    """Build one order document with line items embedded.

    Line items live inside the order because they are always read and written
    with their parent, there are only a handful per order, and nothing queries
    them independently.

    Roughly a third of orders carry a second, *distinct* product. The second
    SKU must differ from the first: repeating a SKU within one order would
    push the same ``order_date`` into the detector twice, creating a bogus
    zero-day interval that drags the computed cadence down.
    """
    line_items = [
        {"sku": product["sku"], "quantity": 1, "unit_price": product["unit_price"]}
    ]
    if rng.randint(1, 3) == 1:
        others = [p for p in catalog if p["sku"] != product["sku"]]
        if others:
            second = rng.choice(others)
            line_items.append(
                {
                    "sku": second["sku"],
                    "quantity": rng.randint(1, 3),
                    "unit_price": second["unit_price"],
                }
            )

    return {
        "customer_id": customer["customer_id"],
        "order_date": order_date,
        "line_items": line_items,
    }


def _upsert(collection, docs: Sequence[Dict[str, Any]], key: str) -> None:
    """Bulk-upsert ``docs`` keyed on ``key``, leaving existing documents alone."""
    if not docs:
        return
    collection.bulk_write(
        [UpdateOne({key: d[key]}, {"$setOnInsert": d}, upsert=True) for d in docs],
        ordered=False,
    )


# ---------------------------------------------------------------------------
# Pattern detection
# ---------------------------------------------------------------------------

#: Core pipeline stages shared by both full-rebuild and incremental modes.
#: The leading ``$match`` and trailing observation-count filter are
#: prepended/appended dynamically by ``_build_pipeline``.
#:
#: Only operators supported across all DocumentDB versions are used:
#: ``$unwind``, ``$group``, ``$match``, and ``$project``.
_GROUP_STAGES: List[Dict[str, Any]] = [
    {"$unwind": "$line_items"},
    {
        "$group": {
            "_id": {"customer_id": "$customer_id", "sku": "$line_items.sku"},
            "order_dates": {"$push": "$order_date"},
            "observation_count": {"$sum": 1},
            "last_purchase_date": {"$max": "$order_date"},
        }
    },
]

_PROJECT_STAGE: Dict[str, Any] = {
    "$project": {
        "_id": 0,
        "customer_id": "$_id.customer_id",
        "sku": "$_id.sku",
        "observation_count": 1,
        "last_purchase_date": 1,
        "order_dates": 1,
    }
}


def _build_pipeline(since: datetime, full_rebuild: bool) -> List[Dict[str, Any]]:
    """Build the aggregation pipeline with ``$match`` as the first stage.

    In full-rebuild mode the pipeline filters out pairs below
    MIN_OBSERVATIONS server-side. In incremental mode that filter is omitted
    because a pair may have only one new order but many prior observations.
    """
    stages: List[Dict[str, Any]] = [{"$match": {"order_date": {"$gte": since}}}]
    stages.extend(_GROUP_STAGES)
    if full_rebuild:
        stages.append({"$match": {"observation_count": {"$gte": MIN_OBSERVATIONS}}})
    stages.append(_PROJECT_STAGE)
    return stages


def _get_last_run_watermark(db):
    """Read the timestamp of the last successful detection run."""
    doc = db.checkpoints.find_one({"_id": "pattern_detection"})
    return doc["last_run"] if doc else None


def _set_last_run_watermark(db, timestamp: datetime) -> None:
    """Persist the detection run timestamp for the next incremental pass."""
    db.checkpoints.update_one(
        {"_id": "pattern_detection"},
        {"$set": {"last_run": timestamp}},
        upsert=True,
    )



def compute_confidence(
    observation_count: int, avg_interval: float, stddev_interval: float
) -> float:
    """Score how trustworthy a detected cadence is, from 0.0 to 1.0.

    Two factors multiplied together:

    * **Evidence** - ``min(1, observations / 10)``. More purchases mean more
      confidence, saturating at ten.
    * **Stability** - ``1 - min(1, stddev / mean)``. Punishes erratic gaps via
      the coefficient of variation. Clockwork intervals score 1.0; intervals
      as noisy as they are long score 0.0.

    Returns ``0.0`` for a non-positive mean interval, which would otherwise
    divide by zero.
    """
    if avg_interval <= 0:
        return 0.0
    evidence = min(1.0, observation_count / 10.0)
    stability = max(0.0, 1.0 - min(1.0, stddev_interval / avg_interval))
    return round(evidence * stability, 4)


def _intervals_from_dates(order_dates: Sequence[datetime]) -> List[float]:
    """Return gaps between consecutive purchases, in days."""
    ordered = sorted(order_dates)
    return [
        (b - a).total_seconds() / 86400.0 for a, b in zip(ordered, ordered[1:])
    ]


def _welford_from_intervals(intervals: Sequence[float]) -> Tuple[int, float, float]:
    """Bootstrap Welford state (count, mean, m2) from a batch of intervals."""
    n = 0
    mean = 0.0
    m2 = 0.0
    for x in intervals:
        n += 1
        delta = x - mean
        mean += delta / n
        delta2 = x - mean
        m2 += delta * delta2
    return n, mean, m2


def _welford_merge(
    n_a: int, mean_a: float, m2_a: float,
    n_b: int, mean_b: float, m2_b: float,
) -> Tuple[int, float, float]:
    """Combine two independent Welford states in O(1) (Chan's algorithm)."""
    if n_a == 0:
        return n_b, mean_b, m2_b
    if n_b == 0:
        return n_a, mean_a, m2_a
    n = n_a + n_b
    delta = mean_b - mean_a
    mean = mean_a + delta * (n_b / n)
    m2 = m2_a + m2_b + delta * delta * n_a * n_b / n
    return n, mean, m2


def _stddev_from_welford(n: int, m2: float) -> float:
    """Compute sample standard deviation from Welford state."""
    if n < 2:
        return 0.0
    return sqrt(m2 / (n - 1))


def _process_chunk(
    chunk: List[Dict[str, Any]],
    db,
    full_rebuild: bool,
    confidence_threshold: float,
    now: datetime,
) -> List[UpdateOne]:
    """Process a batch of aggregation results into pattern upserts.

    In incremental mode, fetches all existing patterns for the chunk in a
    single ``$in`` query on ``_id`` - one round-trip per batch instead of
    one per document.
    """
    existing_map: Dict[str, Dict[str, Any]] = {}
    if not full_rebuild:
        pattern_ids = [
            f"{g['customer_id']}:{g['sku']}" for g in chunk
        ]
        for doc in db.purchase_patterns.find(
            {"_id": {"$in": pattern_ids}},
            projection={
                "observation_count": 1,
                "last_purchase_date": 1,
                "interval_count": 1,
                "interval_mean": 1,
                "interval_m2": 1,
            },
        ):
            existing_map[doc["_id"]] = doc

    operations = []
    for group in chunk:
        pattern_id = f"{group['customer_id']}:{group['sku']}"
        new_dates = sorted(group["order_dates"])

        if full_rebuild:
            observation_count = group["observation_count"]
            if observation_count < MIN_OBSERVATIONS:
                continue
            intervals = _intervals_from_dates(new_dates)
            n, mean, m2 = _welford_from_intervals(intervals)
            last_purchase = new_dates[-1]
        else:
            existing = existing_map.get(pattern_id)

            if existing:
                bridge_interval = (
                    new_dates[0] - existing["last_purchase_date"]
                ).total_seconds() / 86400.0
                within_intervals = _intervals_from_dates(new_dates)
                new_intervals = [bridge_interval] + within_intervals

                n_new, mean_new, m2_new = _welford_from_intervals(new_intervals)
                n, mean, m2 = _welford_merge(
                    existing["interval_count"],
                    existing["interval_mean"],
                    existing["interval_m2"],
                    n_new, mean_new, m2_new,
                )
                observation_count = existing["observation_count"] + len(new_dates)
                last_purchase = new_dates[-1]
            else:
                observation_count = len(new_dates)
                if observation_count < MIN_OBSERVATIONS:
                    continue
                intervals = _intervals_from_dates(new_dates)
                n, mean, m2 = _welford_from_intervals(intervals)
                last_purchase = new_dates[-1]

            if observation_count < MIN_OBSERVATIONS:
                continue

        stddev = _stddev_from_welford(n, m2)
        confidence = compute_confidence(observation_count, mean, stddev)
        pattern = {
            "customer_id": group["customer_id"],
            "sku": group["sku"],
            "observation_count": observation_count,
            "interval_count": n,
            "interval_mean": mean,
            "interval_m2": m2,
            "average_interval_days": round(mean, 2),
            "interval_stddev_days": round(stddev, 2),
            "confidence": confidence,
            "last_purchase_date": last_purchase,
            "computed_at": now,
        }
        operations.append(
            UpdateOne(
                {"_id": pattern_id},
                {"$set": pattern},
                upsert=True,
            )
        )

        if confidence < confidence_threshold:
            db.reorder_recommendations.delete_one({"_id": pattern_id})

    return operations


def detect_patterns(db, full_rebuild: bool = False, confidence_threshold: float = 0.4) -> int:
    """Find recurring ``(customer, SKU)`` cadences and store them.

    Builds a pipeline with ``$match`` as the first stage so DocumentDB uses
    the ``order_date_asc`` index. In incremental mode, only orders newer than
    the last run are scanned; new intervals are merged into running statistics
    (Welford's algorithm) stored on each pattern document.

    The ``_id`` is the deterministic composite ``"{customer_id}:{sku}"``, so
    re-running updates each pattern in place instead of accumulating copies.

    Aggregation results are processed in batches of ``BULK_BATCH_SIZE``. In
    incremental mode, each batch fetches existing patterns with a single
    ``$in`` query - one round-trip per batch instead of one per document.

    When a pattern's confidence drops below ``confidence_threshold``, its
    corresponding recommendation is deleted immediately - a targeted point
    delete on the shared ``_id``, avoiding any bulk reconciliation step.

    Returns the number of patterns written.
    """
    now = datetime.now(timezone.utc)
    total = 0

    if full_rebuild:
        since = now - timedelta(days=DETECTION_WINDOW_DAYS)
        log.info(
            "Full rebuild: scanning orders from last %d days", DETECTION_WINDOW_DAYS
        )
    else:
        last_run = _get_last_run_watermark(db)
        if last_run:
            since = last_run
            log.info("Incremental run: orders after %s", since)
        else:
            since = now - timedelta(days=DETECTION_WINDOW_DAYS)
            log.info("No prior run found, using full %d-day window", DETECTION_WINDOW_DAYS)

    pipeline = _build_pipeline(since, full_rebuild)

    chunk: List[Dict[str, Any]] = []
    for group in db.orders.aggregate(pipeline, allowDiskUse=True):
        chunk.append(group)
        if len(chunk) >= BULK_BATCH_SIZE:
            operations = _process_chunk(
                chunk, db, full_rebuild, confidence_threshold, now
            )
            if operations:
                db.purchase_patterns.bulk_write(operations, ordered=False)
                total += len(operations)
            chunk = []

    if chunk:
        operations = _process_chunk(
            chunk, db, full_rebuild, confidence_threshold, now
        )
        if operations:
            db.purchase_patterns.bulk_write(operations, ordered=False)
            total += len(operations)

    _set_last_run_watermark(db, now)
    log.info("Detected %d purchase patterns", total)
    return total


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


def classify_urgency(today: date, next_expected: date) -> str:
    """Label a reorder ``overdue``, ``due_now``, or ``upcoming``.

    The three labels partition the timeline. Because the overdue test is
    strict and runs first, the boundary day itself counts as ``due_now``.
    """
    if today > next_expected + timedelta(days=OVERDUE_GRACE_DAYS):
        return "overdue"
    if today >= next_expected - timedelta(days=DUE_NOW_WINDOW_DAYS):
        return "due_now"
    return "upcoming"


def generate_recommendations(db, confidence_threshold: float) -> int:
    """Turn confident purchase patterns into ranked reorder recommendations.

    Projects only the five fields needed, so the query reads less than the
    full pattern document. The expected reorder date is the last purchase
    plus the average interval; urgency comes from comparing it to today.

    Reuses the same deterministic ``_id`` scheme as the detector, keeping the
    step idempotent. Stale recommendations are already removed by the
    detector when a pattern's confidence drops below threshold - this
    function only upserts.

    Returns the number of recommendations written.
    """
    today = datetime.now(timezone.utc).date()
    now = datetime.now(timezone.utc)
    operations = []
    total = 0

    patterns = db.purchase_patterns.find(
        {"confidence": {"$gte": confidence_threshold}},
        projection={
            "_id": 0,
            "customer_id": 1,
            "sku": 1,
            "average_interval_days": 1,
            "last_purchase_date": 1,
            "confidence": 1,
        },
    )

    for pattern in patterns:
        last = pattern["last_purchase_date"]
        last_date = last.date() if isinstance(last, datetime) else last
        next_expected = last_date + timedelta(
            days=round(pattern["average_interval_days"])
        )
        rec_id = f"{pattern['customer_id']}:{pattern['sku']}"
        recommendation = {
            "customer_id": pattern["customer_id"],
            "sku": pattern["sku"],
            "next_expected_reorder_date": datetime.combine(
                next_expected, dtime.min, tzinfo=timezone.utc
            ),
            "urgency_status": classify_urgency(today, next_expected),
            "confidence": pattern["confidence"],
            "generated_at": now,
        }
        operations.append(
            UpdateOne(
                {"_id": rec_id},
                {"$set": recommendation},
                upsert=True,
            )
        )

        if len(operations) >= BULK_BATCH_SIZE:
            db.reorder_recommendations.bulk_write(operations, ordered=False)
            total += len(operations)
            operations = []

    if operations:
        db.reorder_recommendations.bulk_write(operations, ordered=False)
        total += len(operations)

    log.info("Generated %d reorder recommendations", total)
    return total


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def print_report(db, limit: int = 15) -> None:
    """Print the detected patterns and the ranked reorder list.

    Both reads use a projection and a ``limit`` so neither can pull an
    unbounded result set.

    Recommendations are fetched in expected-date order - which the compound
    index serves - then ranked by urgency in Python. A server-side sort on
    ``urgency_status`` would order the labels alphabetically
    (``due_now`` < ``overdue`` < ``upcoming``), which is not the priority we
    want.
    """
    print("\n" + "=" * 74)
    print(f" TOP PURCHASE PATTERNS BY CONFIDENCE (showing {limit})")
    print("=" * 74)
    print(f"{'CUSTOMER':<12}{'SKU':<28}{'BUYS':>6}{'EVERY':>10}{'CONF':>8}")
    print("-" * 74)
    patterns = (
        db.purchase_patterns.find(
            {},
            projection={
                "_id": 0,
                "customer_id": 1,
                "sku": 1,
                "observation_count": 1,
                "average_interval_days": 1,
                "confidence": 1,
            },
        )
        .sort([("confidence", -1)])
        .limit(limit)
    )
    for p in patterns:
        every = f"{p['average_interval_days']:.0f}d"
        print(
            f"{p['customer_id']:<12}{p['sku']:<28}"
            f"{p['observation_count']:>6}{every:>10}{p['confidence']:>8.2f}"
        )

    print("\n" + "=" * 74)
    print(f" REORDER RECOMMENDATIONS, MOST URGENT FIRST (showing {limit})")
    print("=" * 74)
    print(f"{'URGENCY':<11}{'CUSTOMER':<12}{'SKU':<28}{'DUE':>12}{'CONF':>8}")
    print("-" * 74)
    recommendations = list(
        db.reorder_recommendations.find(
            {},
            projection={
                "_id": 0,
                "customer_id": 1,
                "sku": 1,
                "next_expected_reorder_date": 1,
                "urgency_status": 1,
                "confidence": 1,
            },
        )
        .sort([("next_expected_reorder_date", 1)])
        .limit(limit)
    )
    recommendations.sort(
        key=lambda r: (
            URGENCY_RANK[r["urgency_status"]],
            r["next_expected_reorder_date"],
        )
    )
    for r in recommendations:
        due = r["next_expected_reorder_date"].strftime("%Y-%m-%d")
        print(
            f"{r['urgency_status']:<11}{r['customer_id']:<12}{r['sku']:<28}"
            f"{due:>12}{r['confidence']:>8.2f}"
        )

    counts = {"overdue": 0, "due_now": 0, "upcoming": 0}
    for doc in db.reorder_recommendations.aggregate([
        {"$group": {"_id": "$urgency_status", "count": {"$sum": 1}}}
    ]):
        if doc["_id"] in counts:
            counts[doc["_id"]] = doc["count"]
    print("-" * 74)
    print(
        f" Totals: {counts['overdue']} overdue | "
        f"{counts['due_now']} due now | {counts['upcoming']} upcoming"
    )
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _pause(message: str, interactive: bool) -> None:
    """Print a stage explanation and wait for the user to continue."""
    if not interactive:
        return
    print(f"\n{'─' * 74}")
    print(message)
    print(f"{'─' * 74}")
    input("Press Enter to continue...")
    print()


_SAMPLE_COLLECTIONS = [
    "customers", "products", "orders",
    "purchase_patterns", "reorder_recommendations", "checkpoints",
]


def _cleanup(db, quiet: bool = False) -> None:
    """Drop all collections created by this sample.

    Run this when you are finished with the demo to remove all data from
    the cluster. Leaves no collections, indexes, or documents behind.
    """
    for name in _SAMPLE_COLLECTIONS:
        db.drop_collection(name)
    if not quiet:
        log.info(
            "Cleanup complete: dropped collections %s",
            ", ".join(_SAMPLE_COLLECTIONS),
        )


def main() -> int:
    """Run the sample end to end."""
    interactive = "--no-pause" not in sys.argv

    config = load_config()
    client = connect(config)
    try:
        db = client[config["database"]]

        if "--cleanup" in sys.argv:
            _cleanup(db)
            log.info("All sample data removed.")
            return 0

        _cleanup(db, quiet=True)
        ensure_indexes(db)

        _pause(
            "STEP 1: SEED SAMPLE DATA\n\n"
            "Generating 12 customers, 18 products, and ~200 days of order\n"
            "history.\n\n" 
            "Each customer buys 2-4 products on a recurring cadence\n"
            "with a day of jitter. About a third of series stop early and\n"
            "become 'overdue' recommendations.",
            interactive,
        )
        seed_sample_data(db)

        full_rebuild = _get_last_run_watermark(db) is None
        _pause(
            "STEP 2: DETECT PURCHASE PATTERNS\n\n"
            "Running an aggregation pipeline with the following stages:\n"
            " * $match  - uses order_date index\n"
            " * $unwind - explodes line items\n" 
            " * $group  - collects dates per customer/SKU pair\n\n"
            "Results are processed in batches, where each batch\n"
            "fetches existing patterns with a single $in query. It then\n"
            "merges new intervals into running statistics and computes\n"
            "a confidence score.",
            interactive,
        )
        detect_patterns(
            db,
            full_rebuild=full_rebuild,
            confidence_threshold=config["confidence_threshold"],
        )

        _pause(
            "STEP 3: GENERATE RECOMMENDATIONS\n\n"
            "Reading patterns above the confidence threshold, projecting only\n"
            "the fields needed, and computing the next expected reorder date\n"
            "as last_purchase_date + average_interval_days.\n\n"
            "Each date is compared to today to classify urgency:\n"
            " * overdue  - more than 2 days past expected\n"
            " * due_now  - within 3 days before through 2 days after\n"
            " * upcoming - more than 3 days out\n\n"
            "If a pattern's confidence dropped below threshold during\n"
            "detection, its recommendation was already deleted.",
            interactive,
        )
        generate_recommendations(db, config["confidence_threshold"])

        _pause(
            "STEP 4: REPORT\n\n"
            "Querying the top patterns by confidence and the most urgent\n"
            "recommendations. Both reads use projections and .limit() so\n"
            "they never pull unbounded result sets.",
            interactive,
        )
        print_report(db)

        log.info("Sample complete.")
        if interactive:
            print(
                "\nTo serve these recommendations via REST API, run:\n"
                "  python api.py\n"
            )
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
