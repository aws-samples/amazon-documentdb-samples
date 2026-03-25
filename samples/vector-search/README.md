# Vector Search Samples for Amazon DocumentDB

Notebooks and applications that demonstrate [vector search](https://docs.aws.amazon.com/documentdb/latest/developerguide/vector-search.html) capabilities in Amazon DocumentDB. Each sample shows a different pattern, from simple semantic search to full RAG chatbots and agentic workflows.

### [RAG Deep Dive](./docdb-rag-deep-dive)

In-depth, guided notebook that builds a RAG chatbot using Amazon DocumentDB as the single store for both source documents and vector embeddings
- Covers HNSW parameter tuning, chunk size/overlap experiments, RAG vs. no-RAG comparison, and production resilience patterns (rate limiting, circuit breakers)
- Uses Amazon Bedrock (Titan Text Embeddings V2 + Claude Haiku 4.5) with a Gradio chat interface

### [Simple RAG Chatbot](./docdb_simple_rag.ipynb)

Uses Amazon Bedrock (Titan Text Embedding + Anthropic Claude), with an optional OpenAI path
- Dataset: [sample transcript from The Motley Fool](./sample-datasets/transcript.txt)

### [Semantic, Text, and Hybrid Search](./semantic_text_hnsw.ipynb)

Illustrates semantic search, text search, and hybrid search using Titan Text Embedding v1
- Dataset: [sample Movies database from Kaggle](./sample-datasets/demomovies.csv)

### [Q&A RAG with LlamaIndex](./docdb-rag-llamaindex.ipynb)

RAG Q&A system using LlamaIndex as the orchestration framework with Titan Text Embedding and Anthropic Claude via Amazon Bedrock
- Dataset: [sample earnings transcript](./sample-datasets/Q1-2024-result-transcript.pdf)

### [Agentic Financial Research Assistant](./agentic-financial-research)

Agentic research assistant combining vector search, text search, and structured queries in a single DocumentDB collection
- Powered by Amazon Bedrock (Claude + Titan Embedding v2) and the Strands Agents SDK
- Dataset: [~500 S&P 500 company profiles](./agentic-financial-research/sp500_enriched.csv)
