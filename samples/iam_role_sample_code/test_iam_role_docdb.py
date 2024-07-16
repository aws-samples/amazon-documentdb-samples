import argparse
import sys
import logging
from datetime import datetime
import pymongo

def main():


    parser = argparse.ArgumentParser(description='Create connections to Amazon DocumentDB cluster .')
    parser.add_argument('--docdb-uri', type=str, required=True, help='Amazon DocumentDB cluster URI (required)')
    args = parser.parse_args()
    ##Create a MongoDB client, open a connection to Amazon DocumentDB as a replica set and specify the read preference as secondary preferred
    client = pymongo.MongoClient(args.docdb_uri) 


    print("------allowed_db-------")
    ##Specify the database to be used
    db = client.allowed_db

    ##Specify the collection to be used
    col = db.sample_collection

    ##Insert a single document
    col.insert_one({'hello':'Amazon DocumentDB'})

    ##Find the document that was previously written
    x = col.find_one({'hello':'Amazon DocumentDB'})

    ##Print the result to the screen

    print(x)

    print("------other_db------")
    ##Specify the database to be used
    db2 = client.other_db
    ##Specify the collection to be used
    col2 = db2.sample_collection

    try :
        ##Insert a single document
        col2.insert_one({'hello':'Amazon DocumentDB'})
    except Exception as e:
        print("Exception trying to insert in other_db :"+ str(e))
        print("------------------")

    try :
        ##Find the document that was previously written
        x = col2.find_one({'hello':'Amazon DocumentDB'})
        ##Print the result to the screen
        print(x)
    except Exception as e:
        print("Exception trying to read in other_db :"+ str(e))
        print("------------------")


    ##Close the connection
    print("--------closing connection----------")
    client.close()

if __name__ == '__main__':
    main()