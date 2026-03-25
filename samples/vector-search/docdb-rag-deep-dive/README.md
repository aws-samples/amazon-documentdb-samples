# Amazon DocumentDB RAG Deep Dive

An in-depth, guided notebook that builds a complete [RAG (Retrieval-Augmented Generation)](https://aws.amazon.com/what-is/retrieval-augmented-generation/) chatbot using [Amazon DocumentDB](https://aws.amazon.com/documentdb/) as the single store for both source documents and [vector embeddings](https://docs.aws.amazon.com/documentdb/latest/developerguide/vector-search.html). Unlike a typical quickstart, this notebook explains *why* each parameter matters and demonstrates the impact of changing them with targeted examples.

Most RAG tutorials show you the "happy path." This notebook goes deeper:

- **Single-store architecture** - vectors and source text live in the same document, eliminating the multi-database sync problem
- **HNSW parameter tuning** - measures recall vs. latency across different `m`, `efConstruction`, and `efSearch` values so you can see the tradeoffs
- **Chunk size and overlap experiments** - demonstrates what happens when chunks split mid-sentence and how overlap preserves context
- **RAG vs. no-RAG comparison** - side-by-side output showing what the LLM gets right (and wrong) without retrieval
- **Production resilience patterns** - rate limiting, circuit breakers, and retry logic for Bedrock API calls

*Check out the [AWS Events YouTube channel](https://www.youtube.com/watch?v=Ww4-BVC6ya8) for a walkthrough of this demo.*

[![Watch the video](https://img.youtube.com/vi/Ww4-BVC6ya8/maxresdefault.jpg)](https://www.youtube.com/watch?v=Ww4-BVC6ya8)

## Architecture

- Amazon DocumentDB (single collection with HNSW index)
- [Amazon Titan Text Embeddings V2](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html)
- Anthropic Claude Haiku 4.5 via [Amazon Bedrock](https://aws.amazon.com/bedrock/)
- Gradio chat interface
- [Amazon SageMaker](https://aws.amazon.com/sagemaker/) or any Jupyter-compatible environment

## Notebook Sections

| # | Section | Purpose |
|---|---------|-------------|
| — | Required Configuration | Secret name, AWS region, connection mode |
| 1 | Install Dependencies | Required Python packages |
| 2 | Import Libraries | Core imports |
| 3 | Resilience Utilities | Rate limiter and circuit breaker decorators |
| 4 | Connect to DocumentDB | Secrets Manager credentials, HNSW index creation |
| 5 | Load and Chunk Documents | PDFs, blog posts, and doc pages → chunked text |
| 6 | Generate Embeddings and Insert | Titan embeddings → batch insert into DocumentDB |
| 7 | Single-Store vs. Multi-Store | Benchmarks the single-collection approach against a multi-collection pattern |
| 8 | HNSW Parameter Tuning | Recall vs. latency across index configurations |
| 9 | Configure LLM and Vector Store | Claude Haiku + DocumentDB vector store setup |
| 10 | Chunk Overlap - Why It Matters | Same document chunked with/without overlap, then queried |
| 11 | Prompt Template | System prompt for grounded Q&A |
| 12 | RAG vs No-RAG Comparison | Side-by-side LLM output with and without retrieval |
| 13 | Chat Configuration | History length and retrieval limits |
| 14 | Launch Chatbot | Gradio chat interface with caching and resilience |
| 15 | Cleanup | Close connections |

## Prerequisites

- AWS account with access to Amazon Bedrock (Titan Text Embeddings V2 and Claude Haiku 4.5)
- Amazon DocumentDB cluster (version 5.0+)
- [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/) secret containing your [Amazon DocumentDB credentials](https://docs.aws.amazon.com/documentdb/latest/developerguide/docdb-secrets-manager.html)
- Python 3.10+

## Sample Data

This notebook ingests PDF documents as its knowledge base. You can use any PDFs, but to reproduce the demo as shown, download:

1. [Amazon DocumentDB Developer Guide (PDF)](https://docs.aws.amazon.com/documentdb/latest/developerguide/developerguide.pdf)
2. [Data Modeling with Amazon DocumentDB (PDF)](https://d1.awsstatic.com/product-marketing/Data%20modeling%20with%20Amazon%20DocumentDB.pdf)

Place the PDF files in the same directory as the notebook.

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Download the [Amazon DocumentDB TLS certificate](https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem):

   ```bash
   wget https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
   ```

3. Download the sample PDFs (see [Sample Data](#sample-data) above) into this directory.

4. Open `docdb-rag-deep-dive.ipynb` and update the **Required Configuration** cell at the top:
   - `secret_name` — your Secrets Manager secret name
   - `aws_region` — your AWS region
   - `is_bastion` — set to `'y'` if connecting through a bastion host

5. Run the notebook cells sequentially.
