import argparse
import boto3
import json
import pymongo
from pymongo.encryption import Algorithm, ClientEncryption

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
        secret_username, secret_password, cluster_uri = get_credentials(SECRET_NAME)

        # Create the connection to the Amazon DocumentDB cluster
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

def generate_keys(args):
    client = connect_docdb(SECRET_NAME)

    # Key generation logic
    try:
        kms_providers = {
            "aws": { }
        }

        # Namespace where data keys are stored (<database>.<collection>)
        key_vault_namespace = args.key_vault
        
        # Data key alt name
        keyAltName = args.key_alt_name

        key_vault_db_name, key_vault_coll_name = key_vault_namespace.split(".", 1)
        key_vault = client[key_vault_db_name][key_vault_coll_name]
        
        # Ensure that two data keys cannot share the same keyAltName
        key_vault.create_index("keyAltNames", unique=True)

        client_encryption = ClientEncryption(
            kms_providers, key_vault_namespace, client, client.codec_options
        )

        m_key = {"region": AWS_REGION, "key": KMS_KEY_ARN}

        data_key_id = client_encryption.create_data_key(
            "aws", master_key=m_key, key_alt_names=[keyAltName]
        )

        doc = key_vault.find_one(
            {"keyAltNames": keyAltName},
            {"_id": 1, "keyAltNames": 1, "creationDate": 1, "updateDate": 1},
        )

        print("Created data key named: ", doc["keyAltNames"], "\n", "Created date:", doc["creationDate"])

        client_encryption.close()
        client.close()
    except Exception as e:
        print('Failed to generate key because: {}'.format(e))


def list_keys(args):
    client = connect_docdb(SECRET_NAME)

    try:
        key_vault_namespace = args.key_vault
        key_vault_db_name, key_vault_coll_name = key_vault_namespace.split(".", 1)
        key_vault = client[key_vault_db_name][key_vault_coll_name]

        # Find all documents in the key vault
        cursor = key_vault.find({}, {"_id": 1, "keyAltNames": 1})
        for doc in cursor:
            object_id_hex = str(doc["_id"].hex())
            print("_id:", object_id_hex)
            print("keyAltNames:", doc.get("keyAltNames", []))
            print()

        client.close()
    except Exception as e:
        print('Failed to list keys because: {}'.format(e))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate and manage data keys for Amazon DocumentDB clilent side field level encryption")
    parser.add_argument("action", choices=["create", "list"], help="[Required] Action to perform: create new data key or list existing keys")
    parser.add_argument("--key-vault", required=True, help="[Required] The namespace where the data keys are stored, in the format '<database>.<collection>'")
    # Add the --key-alt-name argument with required=False by default, but required for the create action
    parser.add_argument("--key-alt-name", required=False, help="[Required for the 'create' action] The data Key Alt Name")

    args = parser.parse_args()

    if args.action == "create":
        if args.key_alt_name is None:
            parser.error("--key-alt-name is required for the 'create' action.")
        generate_keys(args)
    elif args.action == "list":
        list_keys(args)
