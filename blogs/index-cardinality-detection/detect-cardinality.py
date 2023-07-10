import pymongo
import boto3
import json
from datetime import datetime
import csv

def sample_documents_based_on_index(collection, key):
    documents = collection.distinct(key)
    return documents

def main(connection_string='', max_collections=100, threshold=0.01):
    """main functions takes two arguments (uses default values if args not provided)"""

    if not connection_string:
        raise ValueError('Connection String missing!')

    
    client = pymongo.MongoClient(connection_string)

    
    indexes_count = 0
    collections_count = 0
    database_count = 0
    indexes_with_below_threshold_cardinality = 0
    try:
        databases = client.list_database_names()
        database_count = len(databases)
        results = []
        for database_name in databases:
            database = client[database_name]
            collections = database.list_collection_names()
            collections_count = collections_count + len(collections)
            
            for collection_name in collections[:max_collections]:
                collection = database[collection_name]
                indexes = list(collection.list_indexes())
                #indexes_count = indexes_count + len(indexes)
                for index in indexes:
                    for key in index['key']:
                        if key != '_id':
                            distinct_values = sample_documents_based_on_index(
                                collection, key)
                            distinct_count = len(distinct_values)
                            total_count = collection.count_documents({})
                            if total_count == 0:
                                continue

                            cardinality = distinct_count / total_count
                            rounded_cardinality = round(cardinality, 4)
                            unique_records = distinct_values[:10]
                            indexes_count = indexes_count + 1
                            # threshold_breached set to either true or false
                            threshold_breached = cardinality < threshold

                            # if it's true, then set the variable to Y otherwise N
                            if threshold_breached:
                                threshold_breached = 'Y'
                                indexes_with_below_threshold_cardinality = indexes_with_below_threshold_cardinality + 1
                            else:
                                threshold_breached = 'N'

                            # print statement to help debug
                            print('cardinality=', cardinality,
                                  'hence threshold breached = ', threshold_breached)

                            result_dict = {
                                'colname': key, 'index name': index['name'],
                                'cardinality %': rounded_cardinality,
                                'date sampled': datetime.now().isoformat(),
                                'List of Unique records ( max 10 )': unique_records,
                                'threshold breached (Y/N)': threshold_breached}

                            #print('result_dict', result_dict)
                            results.append(result_dict)

        keys = results[0].keys()
        date_now = str(datetime.now().isoformat())
        csv_file_name = f'results-{date_now}.csv'
        with open(csv_file_name, 'w', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(results)
        
        print('\n')
        print('----------------------------------------')
        print(f'Total Databases Found: {database_count}')
        print(f'Total Collections across Databases Found: {collections_count}')
        print(f'Total Indexes across Collections: {indexes_count}')
        print('----------------------------------------')
        print(f'Found {indexes_with_below_threshold_cardinality} index(es) with cardinality <= {threshold * 100}% across {collections_count} collection(s) and {database_count} database(s).')
        print(f'Check the CSV file generated at {csv_file_name} for details.')

      

    except Exception as e:
        print("An error occurred:", e)


# insert two parameters here if not using the defaults
if __name__ == "__main__":
    conn_string = ''
    main(conn_string)
