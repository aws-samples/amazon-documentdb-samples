import pymongo
import boto3
import json
from datetime import datetime
import csv


def get_secret(secret_name='DocumentDBConnection', region_name="us-east-1"):
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager', region_name=region_name)
    get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    secret = get_secret_value_response['SecretString']
    return json.loads(secret)


def sample_documents_based_on_index(collection, key):
    documents = collection.distinct(key)
    return documents


def main(secret_name='DocumentDBConnection', threshold=.99):
    """main functions takes two arguments (uses default values if args not provided)"""

    secret = get_secret(secret_name=secret_name)
    cluster_endpoint = secret['cluster_endpoint']
    username = secret['username']
    password = secret['password']
    
    # use the first connection string if TLS is enabled and the second if disabled      
    #client = pymongo.MongoClient(f'mongodb://{username}:{password}@{cluster_endpoint}:27017/?tls=true&tlsCAFile=us-east-1-bundle.pem')    
    client = pymongo.MongoClient(
        f'mongodb://{username}:{password}@{cluster_endpoint}:27017/')
    
    try:
        databases = client.list_database_names()
        results = []
        for database_name in databases:
            database = client[database_name]
            collections = database.list_collection_names()

            for collection_name in collections:
                collection = database[collection_name]
                indexes = list(collection.list_indexes())

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

                            # threshold_breached set to either true or false
                            threshold_breached = cardinality < threshold

                            # if it's true, then set the variable to Y otherwise N
                            if threshold_breached:
                                threshold_breached = 'Y'
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
                            
                            print('result_dict', result_dict)
                            results.append(result_dict)

        keys = results[0].keys()
        date_now = str(datetime.now().isoformat())
        csv_file_name = f'results-{date_now}.csv'
        with open(csv_file_name, 'w', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(results)


        s3 = boto3.resource('s3')
        BUCKET = "jdlcardinalityresults"
        s3.Bucket(BUCKET).upload_file(csv_file_name, 'results/' + csv_file_name)
        
    except Exception as e:
        print("An error occurred:", e)

#insert two parameters here if not using the defaults
if __name__ == "__main__":
    main()

