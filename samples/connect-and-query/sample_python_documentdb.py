import os
import sys
import pymongo

#Insert sample data
SEED_DATA = [
{ "_id" : 1, "name" : "Tim", "status": "active", "level": 12, "score":202},
{ "_id" : 2, "name" : "Justin", "status": "inactive", "level": 2, "score":9},
{ "_id" : 3, "name" : "Beth", "status": "active", "level": 7, "score":87},
{ "_id" : 4, "name" : "Jesse", "status": "active", "level": 3, "score":27}
]

#Get Amazon DocumentDB ceredentials from environment variables
username = os.environ.get("docdbUser")
password = os.environ.get("docdbPass")
clusterendpoint = os.environ.get("docdbEndpoint")


def main(args):
    #Establish DocumentDB connection
    client = pymongo.MongoClient(clusterendpoint, username=username, password=password, tls='true', tlsCAFile='rds-combined-ca-bundle.pem',retryWrites='false')
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
    profiles.update(query, {'$set': {'level': 4}})
    print(profiles.find_one(query))

    #Clean up
    db.drop_collection('profiles')
    client.close()

if __name__ == '__main__':
    main(sys.argv[1:])
