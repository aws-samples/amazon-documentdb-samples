# AI-Powered S&P 500 Research Assistant

An agentic financial research assistant that uses Amazon DocumentDB for vector search, text search, and structured queries — all in one database. Powered by Amazon Bedrock and the Strands Agents SDK.

## Why DocumentDB for AI?

This demo shows how a single DocumentDB collection can replace the typical multi-database AI stack:

- **Flexible schemas** — structured metrics, unstructured descriptions, and 1024-dim embeddings live in the same document
- **Native vector search** — HNSW index for semantic similarity, no separate vector database needed
- **Text search** — weighted text index for keyword matching with relevance scoring
- **Aggregation pipelines** — compound indexes for filtering and sorting
- **MongoDB-compatible** — use familiar pymongo drivers and query syntax

## Architecture

```
User → Streamlit UI → Strands Agent → Amazon Bedrock (Claude + Titan Embeddings)
                                    → Amazon DocumentDB (vector + text + structured queries)
```

## Agent Tools & DocumentDB Indexes

| Tool | What It Does | DocumentDB Index |
|------|-------------|-----------------|
| `semantic_search` | Find companies by meaning ("AI chip makers") | HNSW Vector (cosine, 1024d) |
| `keyword_search` | Exact keyword matching ("lithium", "insulin") | Compound Text (weighted) |
| `filter_by_sector` | List companies in a GICS sector | Compound (sector + marketCap) |
| `compare_metrics` | Rank companies by financial metric | Collection scan |
| `get_company_detail` | Full profile for one company | Collection scan |

## Dataset

~500 S&P 500 company profiles with:
- Business descriptions (embedded via Bedrock Titan)
- GICS sector/sub-industry classification
- 16 financial metrics (market cap, revenue, margins, P/E, etc.)

## Prerequisites

- Python 3.10+
- AWS account with access to Amazon Bedrock (Claude and Titan Embedding models)
- Amazon DocumentDB cluster (or local MongoDB with vector search support)
- SSH tunnel to DocumentDB if connecting through a bastion host

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure AWS credentials

```bash
aws configure
# or use your preferred credential method
```

### 3. Set DocumentDB connection string

Create a `.env` file in the project root (already gitignored):

```bash
DOCDB_URI=mongodb://user:pass@localhost:27017/?tls=true&tlsCAFile=global-bundle.pem&retryWrites=false&tlsAllowInvalidHostnames=true&directConnection=true
```

Or export it directly:
```bash
export DOCDB_URI="mongodb://user:pass@localhost:27017/?tls=true&tlsCAFile=global-bundle.pem&retryWrites=false&directConnection=true"
```

If connecting through an SSH tunnel (required for VPC-only DocumentDB clusters):
```bash
ssh -i your-key.pem -L 27017:your-cluster.docdb.amazonaws.com:27017 ec2-user@bastion-host -N
```

### 4. Download the DocumentDB TLS certificate

```bash
wget https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
```

### 5. Ingest data

Ingest the S&P 500 dataset into DocumentDB with embeddings and indexes:
```bash
python ingest_sp500.py
```

This creates the collection with all documents, embeddings, and three indexes (HNSW vector, text, compound).

### 6. Run the app

```bash
streamlit run app.py
```

## Project Structure

```
├── agent.py            # Strands agent with 5 DocumentDB-backed tools
├── app.py              # Streamlit UI with streaming and tool tracking
├── ingest_sp500.py     # Data ingestion: CSV → embeddings → DocumentDB
├── sp500_enriched.csv  # S&P 500 dataset with company profiles and metrics
├── requirements.txt    # Python dependencies
├── .env.example        # Example DocumentDB connection string
├── .env                # DocumentDB connection string (gitignored)
├── global-bundle.pem   # DocumentDB TLS certificate (gitignored)
└── README.md
```

## AWS Services Used

- **Amazon DocumentDB** — document storage, vector search (HNSW), text search, aggregation
- **Amazon Bedrock** — Claude (LLM reasoning), Titan Embedding v2 (1024-dim vectors)
