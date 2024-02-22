# Code samples of vector search for Amazon DocumentDB

## Chatbot demo using vector search for Amazon DocumentDB
- File Name: [docdb_simple_rag](https://github.com/aws-samples/amazon-documentdb-samples/blob/master/samples/vector-search/docdb_simple_rag.ipynb)
- Notebook was tested using python 3.8, langchain  0.1.0, pymongo 4.6.1, gradio 4.14.0
- Uses Amazon DocumentDB 5.0 as vector store with HNSW index type 
- Uses Langchain and third party (Open AI) embedding and LLM model. User will need an Open AI key.
- Dataset: You could use this [sample transcript from The Motley Fool](https://github.com/aws-samples/amazon-documentdb-samples/blob/master/samples/vector-search/sample-datasets/transcript.txt) for the demo


## Semantic search demo using vector search for Amazon DocumentDB
- File Name: [semantic_text_hnsw](https://github.com/aws-samples/amazon-documentdb-samples/blob/master/samples/vector-search/semantic_text_hnsw.ipynb)
- Notebook was tested using python 3.8, pymongo 4.6.1, boto3 1.34.14
- Uses vector search and text search on Amazon DocumentDB 5.0 and Amazon Bedrock's Titan Text Embedding Model v1
- Notebook illustrates a simple implementation of semantic search, text search, and hybrid search
- Dataset: You could use this [sample Movies databse from Kaggle](https://github.com/aws-samples/amazon-documentdb-samples/blob/master/samples/vector-search/sample-datasets/demomovies.csv) for the demo
