"""REST API for consuming replenishment recommendations.

Demonstrates how a downstream service queries the derived collections
produced by ``main.py``. Each endpoint uses a projection and the indexes
created at startup, so reads are efficient regardless of collection size.

Run the pipeline first (``python main.py``), then start the API:

    python api.py

Endpoints:

    GET /recommendations                  - all recommendations, most urgent first
    GET /recommendations?urgency=overdue  - filter by urgency status
    GET /recommendations/<customer_id>    - recommendations for one customer
    GET /patterns/<customer_id>           - detected patterns for one customer
    GET /health                           - connection health check
"""

from __future__ import annotations

import os
import sys

import pymongo
from flask import Flask, jsonify, request

APPNAME = "retail-replenishment-api"

app = Flask(__name__)


def get_db():
    """Return the database handle, creating the client on first call."""
    if not hasattr(app, "_db"):
        uri = os.environ.get("DOCDB_URI")
        if not uri:
            print("ERROR: DOCDB_URI environment variable is required.", file=sys.stderr)
            sys.exit(2)
        client = pymongo.MongoClient(
            uri,
            serverSelectionTimeoutMS=5000,
            maxPoolSize=20,
            minPoolSize=1,
            appname=APPNAME,
        )
        database = os.environ.get("DOCDB_DATABASE", "replenishment")
        app._db = client[database]
    return app._db


@app.route("/health")
def health():
    """Verify the database connection is alive."""
    try:
        get_db().client.admin.command("ping")
        return jsonify({"status": "ok"}), 200
    except Exception as exc:
        return jsonify({"status": "error", "detail": str(exc)}), 503


@app.route("/recommendations")
def list_recommendations():
    """Return recommendations, optionally filtered by urgency.

    Query params:
        urgency  - filter by status (overdue, due_now, upcoming)
        limit    - max results (default 50)
    """
    db = get_db()
    query = {}
    urgency = request.args.get("urgency")
    if urgency:
        query["urgency_status"] = urgency

    limit = min(int(request.args.get("limit", "50")), 200)

    docs = list(
        db.reorder_recommendations.find(
            query,
            projection={
                "_id": 0,
                "customer_id": 1,
                "sku": 1,
                "next_expected_reorder_date": 1,
                "urgency_status": 1,
                "confidence": 1,
            },
        )
        .sort([("urgency_status", 1), ("next_expected_reorder_date", 1)])
        .limit(limit)
    )

    for doc in docs:
        doc["next_expected_reorder_date"] = doc["next_expected_reorder_date"].isoformat()

    return jsonify(docs)


@app.route("/recommendations/<customer_id>")
def customer_recommendations(customer_id: str):
    """Return recommendations for a specific customer."""
    db = get_db()
    docs = list(
        db.reorder_recommendations.find(
            {"customer_id": customer_id},
            projection={
                "_id": 0,
                "sku": 1,
                "next_expected_reorder_date": 1,
                "urgency_status": 1,
                "confidence": 1,
            },
        ).sort([("next_expected_reorder_date", 1)])
    )

    for doc in docs:
        doc["next_expected_reorder_date"] = doc["next_expected_reorder_date"].isoformat()

    return jsonify(docs)


@app.route("/patterns/<customer_id>")
def customer_patterns(customer_id: str):
    """Return detected purchase patterns for a specific customer."""
    db = get_db()
    docs = list(
        db.purchase_patterns.find(
            {"customer_id": customer_id},
            projection={
                "_id": 0,
                "sku": 1,
                "observation_count": 1,
                "average_interval_days": 1,
                "confidence": 1,
                "last_purchase_date": 1,
            },
        ).sort([("confidence", -1)])
    )

    for doc in docs:
        doc["last_purchase_date"] = doc["last_purchase_date"].isoformat()

    return jsonify(docs)


def _cleanup():
    """Drop all collections created by the sample."""
    db = get_db()
    collections = [
        "customers", "products", "orders",
        "purchase_patterns", "reorder_recommendations", "checkpoints",
    ]
    for name in collections:
        db.drop_collection(name)
    print(f"Cleanup complete: dropped collections {', '.join(collections)}")
    print("All sample data removed.")


if __name__ == "__main__":
    if "--cleanup" in sys.argv:
        _cleanup()
    else:
        port = int(os.environ.get("API_PORT", "8080"))
        print(f"Starting replenishment API on http://localhost:{port}")
        app.run(host="127.0.0.1", port=port, debug=False)
