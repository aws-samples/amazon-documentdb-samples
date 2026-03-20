# Code samples of vector search for Amazon DocumentDB

## Chatbot/ Simple RAG demo
- File Name: [docdb_simple_rag](./docdb_simple_rag.ipynb)
- Notebook was tested using python 3.8, langchain  0.1.0, pymongo 4.6.1, gradio 4.14.0
- Uses Amazon DocumentDB 5.0 as vector store with HNSW index type 
- Uses Langchain and Amazon Bedrock. Models used are Titan Text Embedding and Anthropic's Claude. User also has an option of choosing third party (Open AI).
- Dataset: You could use this [sample transcript from The Motley Fool](./sample-datasets/transcript.txt) for the demo


## Semantic search demo
- File Name: [semantic_text_hnsw](./semantic_text_hnsw.ipynb)
- Notebook was tested using python 3.8, pymongo 4.6.1, boto3 1.34.14
- Uses vector search and text search on Amazon DocumentDB 5.0 and Amazon Bedrock's Titan Text Embedding Model v1
- Notebook illustrates a simple implementation of semantic search, text search, and hybrid search
- Dataset: You could use this [sample Movies databse from Kaggle](./sample-datasets/demomovies.csv) for the demo


## Q&A RAG demo using Amazon DocumentDB, LlamaIndex and Amazon Bedrock
- File Name: [docdb-rag-llamaindex](./docdb-rag-llamaindex.ipynb)
- Notebook was tested using python 3.8, pymongo 4.7.1, boto3 1.34.71
- This notebook demonstrates the implementation of a Question and Answer (Q&A) system using Retrieval Augmented Generation (RAG). It utilizes Amazon Titan Text Embedding as the embedding model, Anthropic Claude as the Large Language Model (LLM), and Amazon Bedrock as the runtime environment. The LlamaIndex framework is used as RAG orchestratation framework.
- Dataset: You could use this [sample transcript](./sample-datasets/Q1-2024-result-transcript.pdf) for the demo


## Agentic Financial Research Assistant
- File Name: [agentic-financial-research](./agentic-financial-research)
- Tested using Python 3.10+, pymongo 4.6.0, boto3 1.35.0, strands-agents 0.1.0, streamlit 1.30.0
- An agentic research assistant that uses Amazon DocumentDB for vector search, text search, and structured queries — all in one database
- Powered by Amazon Bedrock (Claude for reasoning, Titan Embedding v2 for 1024-dim vectors) and the Strands Agents SDK
- Demonstrates HNSW vector index (semantic search), compound text index (keyword search), and compound index (sector + market cap filtering) on a single collection
- Dataset: ~500 S&P 500 company profiles with business descriptions, GICS classification, and 16 financial metrics (included as [sp500_enriched.csv](./agentic-financial-research/sp500_enriched.csv))
