# Code samples of vector search for Amazon DocumentDB

## Chatbot/ Simple RAG demo
- File Name: [docdb_simple_rag](https://github.com/aws-samples/amazon-documentdb-samples/blob/master/samples/vector-search/docdb_simple_rag.ipynb)
- Notebook was tested using python 3.8, langchain  0.1.0, pymongo 4.6.1, gradio 4.14.0
- Uses Amazon DocumentDB 5.0 as vector store with HNSW index type 
- Uses Langchain and Amazon Bedrock. Models used are Titan Text Embedding and Anthropic's Claude. User also has an option of choosing third party (Open AI).
- Dataset: You could use this [sample transcript from The Motley Fool](https://github.com/aws-samples/amazon-documentdb-samples/blob/master/samples/vector-search/sample-datasets/transcript.txt) for the demo


## Semantic search demo
- File Name: [semantic_text_hnsw](https://github.com/aws-samples/amazon-documentdb-samples/blob/master/samples/vector-search/semantic_text_hnsw.ipynb)
- Notebook was tested using python 3.8, pymongo 4.6.1, boto3 1.34.14
- Uses vector search and text search on Amazon DocumentDB 5.0 and Amazon Bedrock's Titan Text Embedding Model v1
- Notebook illustrates a simple implementation of semantic search, text search, and hybrid search
- Dataset: You could use this [sample Movies databse from Kaggle](https://github.com/aws-samples/amazon-documentdb-samples/blob/master/samples/vector-search/sample-datasets/demomovies.csv) for the demo


## Q&A RAG demo using Amazon DocumentDB, LlamaIndex and Amazon Bedrock
- File Name: [docdb-rag-llamaindex](https://github.com/aws-samples/amazon-documentdb-samples/blob/master/samples/vector-search/docdb-rag-llamaindex.ipynb)
- Notebook was tested using python 3.8, pymongo 4.7.1, boto3 1.34.71
- This notebook demonstrates the implementation of a Question and Answer (Q&A) system using Retrieval Augmented Generation (RAG). It utilizes Amazon Titan Text Embedding as the embedding model, Anthropic Claude as the Large Language Model (LLM), and Amazon Bedrock as the runtime environment. The LlamaIndex framework is used as RAG orchestratation framework.
- Dataset: You could use this [sample transcript](https://github.com/aws-samples/amazon-documentdb-samples/blob/master/samples/vector-search/sample-datasets/Q1-2024-result-transcript.pdf) for the demo
