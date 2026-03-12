"""
S&P 500 Ingestion: Read sp500_enriched.csv, embed longBusinessSummary via Bedrock Titan,
load into DocumentDB with vector index.
"""

import csv
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3
import pymongo
from dotenv import load_dotenv

load_dotenv()

DOCDB_URI = os.environ["DOCDB_URI"]
DB_NAME = "financial_research"
COLLECTION_NAME = "sp500_companies"
EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIMENSION = 1024
AWS_REGION = "us-east-1"
CSV_FILE = "sp500_enriched.csv"
CONCURRENT_WORKERS = 10

NUMERIC_FIELDS = [
    "fullTimeEmployees", "marketCap", "totalRevenue", "revenueGrowth",
    "grossMargins", "operatingMargins", "profitMargins", "returnOnEquity",
    "debtToEquity", "trailingPE", "forwardPE", "dividendYield", "beta",
    "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "currentPrice",
]


def generate_embedding(client, text):
    text = text[:8000]
    resp = client.invoke_model(
        modelId=EMBEDDING_MODEL,
        body=json.dumps({"inputText": text, "dimensions": EMBEDDING_DIMENSION}),
    )
    return json.loads(resp["body"].read())["embedding"]


def parse_numeric(val):
    if not val or val == "":
        return None
    try:
        return float(val)
    except ValueError:
        return None


def create_indexes(db, collection_name):
    col = db[collection_name]
    existing = col.index_information()

    # 1. HNSW vector index for semantic search
    if "vector_index_hnsw" in existing:
        print("  HNSW vector index already exists, skipping.")
    else:
        if "vector_index" in existing:
            print("  Dropping old IVFFlat index...")
            col.drop_index("vector_index")
        print("  Creating HNSW vector index...")
        db.command({
            "createIndexes": collection_name,
            "indexes": [{
                "key": {"embedding": "vector"},
                "name": "vector_index_hnsw",
                "vectorOptions": {
                    "type": "hnsw",
                    "similarity": "cosine",
                    "dimensions": EMBEDDING_DIMENSION,
                    "m": 16,
                    "efConstruction": 64,
                },
            }],
        })
        print("  HNSW vector index created.")

    # 2. Compound text index for keyword search
    if "text_search_index" in existing:
        print("  Text search index already exists, skipping.")
    else:
        print("  Creating compound text index (description, company, industry)...")
        col.create_index(
            [("description", "text"), ("company", "text"), ("industry", "text")],
            weights={"description": 10, "company": 5, "industry": 3},
            name="text_search_index",
        )
        print("  Text search index created.")

    # 3. Compound index for sector filtering sorted by market cap
    if "sector_marketcap" in existing:
        print("  Sector + marketCap index already exists, skipping.")
    else:
        print("  Creating sector + marketCap compound index...")
        col.create_index(
            [("sector", 1), ("metrics.marketCap", -1)],
            name="sector_marketcap",
        )
        print("  Sector + marketCap index created.")


def main():
    print("=" * 60)
    print("S&P 500 Ingestion into DocumentDB")
    print("=" * 60)

    # Read CSV
    print("\n[1/4] Reading CSV...")
    rows = []
    with open(CSV_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    print(f"  Loaded {len(rows)} companies.")

    # Connect
    print("\n[2/4] Connecting...")
    bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    docdb = pymongo.MongoClient(DOCDB_URI)
    db = docdb[DB_NAME]
    collection = db[COLLECTION_NAME]
    collection.drop()
    print("  Connected.")

    # Build documents (without embeddings)
    print(f"\n[3/4] Embedding ({CONCURRENT_WORKERS} concurrent workers) and inserting...")
    start_time = time.time()
    docs = []
    skipped = 0

    for row in rows:
        summary = row.get("longBusinessSummary", "")
        if not summary:
            skipped += 1
            continue

        doc = {
            "symbol": row["Symbol"],
            "company": row["Security"],
            "sector": row["GICS Sector"],
            "sub_industry": row["GICS Sub-Industry"],
            "headquarters": row["Headquarters Location"],
            "founded": row.get("Founded", ""),
            "industry": row.get("industry", ""),
            "description": summary,
        }

        metrics = {}
        for field in NUMERIC_FIELDS:
            val = parse_numeric(row.get(field, ""))
            if val is not None:
                metrics[field] = val
        doc["metrics"] = metrics
        doc["_embed_text"] = f"{doc['company']} ({doc['sector']}, {doc['industry']}): {summary}"
        docs.append(doc)

    # Generate embeddings concurrently
    def embed_doc(idx_doc):
        idx, doc = idx_doc
        doc["embedding"] = generate_embedding(bedrock, doc.pop("_embed_text"))
        return idx, doc

    embedded = 0
    with ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as executor:
        futures = {executor.submit(embed_doc, (i, doc)): i for i, doc in enumerate(docs)}
        for future in as_completed(futures):
            idx, doc = future.result()
            docs[idx] = doc
            embedded += 1
            if embedded % 50 == 0:
                print(f"  Embedded {embedded}/{len(docs)} companies...")

    print(f"  Embedding complete: {embedded} docs in {time.time() - start_time:.1f}s")

    # Batch insert
    BATCH_SIZE = 50
    inserted = 0
    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i:i + BATCH_SIZE]
        collection.insert_many(batch)
        inserted += len(batch)

    print(f"  Inserted: {inserted}, Skipped (no description): {skipped}")

    # Indexes
    print("\n[4/4] Creating indexes...")
    create_indexes(db, COLLECTION_NAME)

    elapsed = time.time() - start_time
    print(f"\nDone! Collection: {DB_NAME}.{COLLECTION_NAME} ({inserted} docs) in {elapsed:.1f}s")
    docdb.close()


if __name__ == "__main__":
    main()
