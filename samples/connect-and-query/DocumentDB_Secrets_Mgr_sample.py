# This sample python application combines the Secrets Manager python code example with 
# the sample python application from the DocumentDB Introdution module.  

import boto3
import base64
from botocore.exceptions import ClientError
import json
import sys
import pymongo


def get_secret():

####START: Change as needed to match your environment#####
    secret_name = "Apps/DocumentDB/getting-started-with-documentdb-cluster"
    region_name = "us-east-1"
####END: Change as needed to match your environment#####

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
    # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    # We rethrow the exception by default.

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
        else:
            decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
            
    # Your code goes here. 
#
    return json.loads(secret)

username = get_secret()['username']
password = get_secret()['password']
host = get_secret()['host']
port = get_secret()['port']

#Insert sample data
SEED_DATA = [
{ "_id" : 1, "name" : "Tim", "status": "active", "level": 12, "score":202},
{ "_id" : 2, "name" : "Justin", "status": "inactive", "level": 2, "score":9},
{ "_id" : 3, "name" : "Beth", "status": "active", "level": 7, "score":87},
{ "_id" : 4, "name" : "Jesse", "status": "active", "level": 3, "score":27}
]

def main(args):
    #Establish DocumentDB connection
    client = pymongo.MongoClient(host, port, username=username, password=password, ssl='true', ssl_ca_certs='rds-combined-ca-bundle.pem')
    db = client.sample_database
    profiles = db['profiles']

    #Insert data
    profiles.insert_many(SEED_DATA)
    print("Successfully inserted data")

    #Find a document
    query = {'name': 'Jesse'}
    print("Printing query results")
    print(profiles.find_one(query))

    #Update a document
    print("Updating document")
    profiles.update_one(query, {'$set': {'level': 4}})
    print(profiles.find_one(query))

    #Clean up
    db.drop_collection('profiles')
    client.close()

if __name__ == '__main__':
    main(sys.argv[1:])
