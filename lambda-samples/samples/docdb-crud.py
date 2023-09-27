import os
import pymongo
import boto3
import logging
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)
headers = {"X-Aws-Parameters-Secrets-Token": os.environ.get('AWS_SESSION_TOKEN')}

## Set the following 3 environment variables in your Lambda function configuration
# 1. DOCDB_SECRET_NAME: The name of the secret in AWS Secrets Manager containing DocumentDB credentials.
# 2. DOCDB_DATABASE: The name of the DocumentDB database.
# 3. DOCDB_COLLECTION: The name of the DocumentDB collection.

def get_credentials(secret_name):
    session = boto3.session.Session()
    try:
        logger.info('Retrieving secret {} from Secrets Manager.'.format(secret_name))
        client = session.client(service_name='secretsmanager', region_name=session.region_name)
        secret_value = client.get_secret_value(SecretId=secret_name)
        secret_json = json.loads(secret_value['SecretString'])
        username = secret_json['username']
        password = secret_json['password']
        cluster_uri = secret_json['host']
        logger.info('Secret {} retrieved from Secrets Manager.'.format(secret_name))
        return (username, password, cluster_uri)
    except Exception as e:
        logger.error('Failed to retrieve secret {} because: {}'.format(secret_name, e))

# Initialize DocumentDB client outside of the handler
client = None

def connect_to_docdb():
    global client
    if client is None:
        try:
            # Retrieve DocumentDB credentials and cluster uri from AWS Secrets Manager
            secret_name = os.environ['DOCDB_SECRET_NAME']
            (secret_username, secret_password, cluster_uri) = get_credentials(secret_name)

            # Retrieve database_name and collection_name from environment variables
            database_name = os.environ['DOCDB_DATABASE']
            collection_name = os.environ['DOCDB_COLLECTION']

            # Connect to Amazon DocumentDB
            logger.info('Creating new DocumentDB client.')
            client = pymongo.MongoClient(
                cluster_uri,
                tls=True,
                retryWrites=False,
                tlsCAFile='/opt/python/global-bundle.pem',
                username=secret_username,
                password=secret_password,
                authSource='admin')
            logger.info('Successfully created new DocumentDB client.')
        except Exception as e:
            logger.error('An error occurred while connecting to DocumentDB: {}'.format(e))
            return None
    return client

def lambda_handler(event, context):
    try:
        # Get or create the DocumentDB client
        client = connect_to_docdb()

        if client:
            database_name = os.environ['DOCDB_DATABASE']
            collection_name = os.environ['DOCDB_COLLECTION']

            db = client[database_name]
            collection = db[collection_name]

            # Insert a document
            document = {'name': 'Amazon DocumentDB', 'port': 27017}
            result = collection.insert_one(document)
            logger.info('Inserted document with ID: {}.'.format(result.inserted_id))

            # Read the document
            document_id = result.inserted_id
            retrieved_document = collection.find_one({'_id': document_id})
            logger.info('Retrieved document: {}'.format(retrieved_document))

            # Update the document and retrieve the updated version
            updated_document = collection.find_one_and_update(
                {'_id': document_id},
                {'$set': {'port': 37017}},
                return_document=pymongo.ReturnDocument.AFTER
            )
            logger.info('Updated document: {}'.format(updated_document))
            logger.info('Document updated successfully')
    except Exception as e:
        logger.error('An error occurred: {}'.format(e))
    finally:
        # Do not close the client here, reusing in subsequent invocations
        pass
