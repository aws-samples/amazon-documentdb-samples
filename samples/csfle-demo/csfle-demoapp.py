import argparse
import boto3
import json
import pymongo
from pymongo.encryption import Algorithm, ClientEncryption
from bson import ObjectId
from pprint import pprint

# Read the variables from the config file
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

SECRET_NAME = config["SECRET_NAME"]
AWS_REGION = config["AWS_REGION"]
KMS_KEY_ARN = config["KMS_KEY_ARN"]


def get_credentials(secret_name):
    try:
        session = boto3.session.Session()
        client = session.client(service_name='secretsmanager', region_name=AWS_REGION)
        secret_value = client.get_secret_value(SecretId=secret_name)
        secret_json = json.loads(secret_value['SecretString'])
        username = secret_json['username']
        password = secret_json['password']
        cluster_uri = secret_json['host']
        return (username, password, cluster_uri)
    except Exception as e:
        print('Failed to retrieve secret {} because: {}'.format(secret_name, e))

def connect_docdb(secret_name):
    try:
        # Retrieve DocumentDB credentials from the secret stored in AWS Secrets Manager
        secret_username, secret_password, cluster_uri = get_credentials(secret_name)

        # Create the connection to your DocumentDB cluster
        client = pymongo.MongoClient(
            cluster_uri,
            username=secret_username,
            password=secret_password,
            tls="true",
            tlsCAFile="global-bundle.pem",
            retryWrites="false",
        )

        return client
    except Exception as e:
        print('Failed to connect to DocumentDB because: {}'.format(e))

def insert_document(client, key_vault_namespace, key_alt_name):
    try:
        # Specify the namespaces for the key vault and user data
        key_vault_db_name, key_vault_coll_name = key_vault_namespace.split(".", 1)
        demoapp_db, customers_coll = "demoapp", "customers"  # Modify this to your database and collection

        # Access the customers collection
        customerCollection = client[demoapp_db][customers_coll]

        # Create a ClientEncryption instance
        client_encryption = ClientEncryption(
            {
                "aws": {}
            },  
            key_vault_namespace,
            client,
            customerCollection.codec_options
        )

        # Generate a unique customer name and email
        customer_name = "Customer" + str(customerCollection.count_documents({}) + 1)
        customer_email = "customer" + str(customerCollection.count_documents({}) + 1) + "@domain.tld"

        # Encrypt the creditCard field
        encrypted_credit_card = client_encryption.encrypt(
            "1234-5678-9012-3456",  # Replace with the actual credit card number
            Algorithm.AEAD_AES_256_CBC_HMAC_SHA_512_Deterministic,
            key_alt_name=key_alt_name,
        )

        # Insert the document
        inserted_document = {
            "_id": ObjectId(),
            "name": customer_name,
            "email": customer_email,
            "creditCard": encrypted_credit_card,
        }
        customerCollection.insert_one(inserted_document)

        # Print the name and _id of the inserted document
        print('Inserted document with name:', customer_name)
        print('_id:', inserted_document["_id"])
    except Exception as e:
        print('Failed to insert document because: {}'.format(e))

def update_document(client, key_vault_namespace, key_alt_name, document_id):
    try:
        demoapp_db, customers_coll = "demoapp", "customers"  # Modify this to your database and collection

        # Access the user collection
        customerCollection = client[demoapp_db][customers_coll]

        # Create a ClientEncryption instance
        client_encryption = ClientEncryption(
            {"aws": {}},  
            key_vault_namespace,
            client,
            customerCollection.codec_options
        )

        # Find a document to update
        document_to_update = customerCollection.find_one({"_id": ObjectId(document_id)})

        if document_to_update:

            # Read the existing, unencrypted value of the creditCard field
            existing_credit_card = document_to_update["creditCard"]

            # Encrypt the existing creditCard value
            encrypted_credit_card = client_encryption.encrypt(
                existing_credit_card,  # Use the existing credit card number
                Algorithm.AEAD_AES_256_CBC_HMAC_SHA_512_Deterministic,
                key_alt_name=key_alt_name,
            )

            customerCollection.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": {"creditCard": encrypted_credit_card}}
            )

            print('Updated document with _id:', document_id)
        else:
            print('Document not found for update.')
    except Exception as e:
        print('Failed to update document because: {}'.format(e))


def read_document(client, key_vault_namespace, document_id):
    try:
        demoapp_db, customers_coll = "demoapp", "customers"  # Modify this to your database and collection

        # Access the customers collection
        customerCollection = client[demoapp_db][customers_coll]

        # Create a ClientEncryption instance
        client_encryption = ClientEncryption(
            {"aws": {}},  # Temporary credentials are used, no need to specify accessKeyId and secretAccessKey
            key_vault_namespace,
            client,
            customerCollection.codec_options
        )

        # Find a document by _id
        document = customerCollection.find_one({"_id": ObjectId(document_id)})

        if document:
            print('Read document with _id:', document_id)
            
            # Explicitly decrypt the field:
            document["creditCard"] = client_encryption.decrypt(document["creditCard"])
            
            # Pretty print the decrypted document
            pprint(document)
        else:
            print('Document not found with _id:', document_id)
    except Exception as e:
        print('Failed to read document because: {}'.format(e))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Insert, update, or read DocumentDB documents with field-level encryption')
    parser.add_argument('action', choices=['insert', 'update', 'read'],
                        help='The action to perform: insert, update, or read')
    parser.add_argument('--key-vault-namespace', required=True,
                        help='The key vault namespace')
    parser.add_argument('--key-alt-name', required=True,
                        help='The key alt name')
    parser.add_argument('--document-id', required=False,
                        help='The _id of the document (for update and read actions)')

    args = parser.parse_args()
    
    client = connect_docdb(SECRET_NAME)

    if args.action == 'insert':
        insert_document(client, args.key_vault_namespace, args.key_alt_name)
    elif args.action == 'update':
        if args.document_id:
            update_document(client, args.key_vault_namespace, args.key_alt_name, args.document_id)
        else:
            print('Please specify --document-id for the update action.')
    elif args.action == 'read':
        if args.document_id:
            read_document(client, args.key_vault_namespace, args.document_id)
        else:
            print('Please specify --document-id for the read action.')
