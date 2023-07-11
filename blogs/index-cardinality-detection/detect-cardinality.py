import pymongo
import boto3
import json
from datetime import datetime
import csv
import argparse, sys
import certifi
import traceback
import pandas as pd 
import numpy as np

global args


def get_param():
    global args
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--connection_string", action="store", default=None, help="DocumentDB connnection string")
    parser.add_argument("-m", "--max_collections", action="store", default=100, help="Maximum number of collections to scan per database. Default 100")
    parser.add_argument("-t", "--threshold", action="store", default="1", help="Percetage of Cardinality threshold. Default 1%")
    parser.add_argument("-d", "--databases", action="store", default="All", help="Comma separated list of database names. Default=All")
    parser.add_argument("-c", "--collections", action="store", default="All", help="Comma separated list of collection names. Default=All")
    
    args = parser.parse_args()

    if args.connection_string is None:
        print("Connection string is required")
        sys.exit(1)    
    

def print_output(results):
    print("\n------------------------------------------")
    print("Total Databases Found: {}".format(args.db_counter))
    print("Total collections Found across {} database(s): {}".format(args.db_counter, args.coll_counter))
    print("Total indexes found : {}".format(args.index_counter))
    print("------------------------------------------")
    
    print("\n------------------------------------------")
    low_cardinal_results = results[results["isLowCardinality"]=="Y"]
    low_cardinal_results = low_cardinal_results.sort_values('cardinality', ascending=True)

    print("######Found {} indexes that may have low cardinality values.".format( len(low_cardinal_results) ))

    
    #sorted_results = sorted(results, key=lambda x: x['cardinality'], reverse=False)
    #sorted_results = results.sort_values('cardinality', ascending=True)
    
    top_indexes = []
    for index, row in low_cardinal_results.iterrows():
        top_indexes.append( '{} : {}%'.format( row['index_name'], row['cardinality']))
    
    print("Top index(es) with lowest cardinality : {}".format(top_indexes) )
    print("------------------------------------------")
    
def save_file(results):
    date_now = str(datetime.now().isoformat())
    file_name = 'cardinality_output_'+date_now+'.csv'
    
    results.sort_values('cardinality', ascending=True).to_csv(file_name, index=False)
    print("Detailed report is generated and saved at `{}`".format(file_name))
    print("##### Done #####")

def start_cardinality_check():
    global args
    results = []
    connection_string = args.connection_string
    max_collections = args.max_collections
    threshold = float(args.threshold) 
    
    try:
        client = pymongo.MongoClient(connection_string)
        
        databases = client.list_database_names()
        if args.databases != "All":
            databases = args.databases.split(",")
        
        db_counter = 0
        coll_counter = 0
        index_counter = 0
        for db_name in databases:
            db_counter = db_counter + 1
            database = client[db_name]
            coll_names = database.list_collection_names()
            if args.collections != "All":
                coll_names = args.collections.split(",")
            for coll_name in coll_names[:max_collections]:
                coll_counter = coll_counter + 1
                collection = database[coll_name]
                indexes = collection.list_indexes()
                for index in indexes:
                    result_row = {}
                    if index['name'] != '_id_':
                        index_name = list(index['key'].keys())[0]
                        total = collection.count_documents({index_name:{"$exists":True}})
                        distinct = len(collection.distinct(index_name))
                        cardinality = 0
                        isLowCardinality = 'N'
                        if total > 0 and distinct > 0:
                            index_counter = index_counter + 1
                            cardinality = (distinct / total) * 100
                            result_row['index_name'] = index_name
                            result_row['collection_name'] = index['ns']
                            result_row['cardinality'] = round(cardinality,4)
                            if cardinality < threshold:
                                isLowCardinality = 'Y'
                            result_row['isLowCardinality'] = isLowCardinality
                            result_row['totalDocsWithIndexValue'] = total
                            result_row['totalDistinctValues'] = distinct
                            results.append(result_row)
                        
                        
            args.db_counter = db_counter
            args.coll_counter = coll_counter
            args.index_counter = index_counter
        
        return pd.DataFrame(results)
        
        
        
    except Exception as e:
        traceback.print_exception(*sys.exc_info())
        print(e)
        
def main():
    output = {}
    get_param()
    print("\nStarting Cardinality Check. Script may take few mins to finish.")
    print("Finding indexes where Cardinality/Distinct Values are less than ( {}% )...\n".format(args.threshold))
    results = start_cardinality_check()
    print_output(results)
    save_file(results)

# insert two parameters here if not using the defaults
if __name__ == "__main__":
    main()
