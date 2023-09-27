import os
import pymongo
import boto3
import json
import logging

# Set up the logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

## Set the following 2 Environment variables in your Lambda Configuration
DOCDB_SECRET_NAME = os.environ['DOCDB_SECRET_NAME']  
THRESHOLD_SECONDS = int(os.environ['THRESHOLD_SECONDS']) 


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
            secret_name = DOCDB_SECRET_NAME
            (secret_username, secret_password, cluster_uri) = get_credentials(secret_name)

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

def kill_long_running_operations():
    try:
        # Get or create the DocumentDB client
        client = connect_to_docdb()

        if client:
            # Get current operations and filter long-running operations
            db = client.admin # Use the admin database to run the currentOp command
            with db.aggregate([
                {"$currentOp": {}},
                {"$match": {"secs_running": {"$gt": THRESHOLD_SECONDS}}}
            ]) as cursor:
                # Initialize a flag to check if operations were found over the threshold
                operations_found = False
                
                # Iterate through the long-running operations and kill them
                for op in cursor:
                    operations_found = True
                    op_id = op["opid"]
                    secs_running = op["secs_running"]
                    command = op["command"]
                    logger.info(f"Killing operation with ID {op_id} (running for {secs_running} seconds)")
                    logger.info(f"Command: {command}")
                    try:
                        # Try to kill the operation
                        db.command("killOp", op=op_id)
                    except pymongo.errors.OperationFailure as e:
                        logger.error(f"Failed to kill operation with ID {op_id}: {str(e)}")

                # If no operations were found over the threshold, log a message
                if not operations_found:
                    logger.info(f"No operations found over the threshold.")
    except Exception as e:
        logger.error("An error occurred:")
        logger.error(str(e))

def lambda_handler(event, context):
    kill_long_running_operations()
