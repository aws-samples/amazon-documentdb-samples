import os
import sys
import json

import pymongo

#Insert sample data

with open('tweets.json') as f:
    SEED_DATA =  json.load(f)


#Get Amazon DocumentDB ceredentials from enviornment variables
username = os.environ.get("USERNAME")
password = os.environ.get("PASSWORD")
clusterendpoint = os.environ.get("DOCDB_ENDPOINT")

def main(args):
    #Establish DocumentDB connection
    client = pymongo.MongoClient(clusterendpoint, username=username, password=password, ssl='true', tlsCAFile='rds-combined-ca-bundle.pem')
    db = client.sampledb
    tweets = db['tweets']
    tweets.insert_many(SEED_DATA)
    print("Successfully inserted data to tweets collection in sampledb")
    client.close()
    
if __name__ == '__main__':
    main(sys.argv[1:])
