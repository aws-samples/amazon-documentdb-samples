#!/bin/env python

import json
import logging
import os
import string
import sys
import time
import boto3
import datetime
from bson import json_util
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from kafka import KafkaProducer                                                               
from elasticsearch import Elasticsearch                                        
import urllib.request                                                    

"""
Read data from a DocumentDB collection's change stream and replicate that data to MSK.

Required environment variables:
DOCUMENTDB_URI: The URI of the DocumentDB cluster to stream from.
DOCUMENTDB_SECRET: Secret Name of the credentials for the DocumentDB cluster in Secrets Manager
STATE_COLLECTION: The name of the collection in which to store sync state.
STATE_DB: The name of the database in which to store sync state.
WATCHED_COLLECTION_NAME: The name of the collection to watch for changes.
WATCHED_DB_NAME: The name of the database to watch for changes.
Iterations_per_sync: How many events to process before syncing state.
Documents_per_run: The max for the iterator loop. 
SNS_TOPIC_ARN_ALERT: The topic to send exceptions.   

Kafka target environment variables:
MSK_BOOTSTRAP_SRV: The URIs of the MSK cluster to publish messages. 

SNS target environment variables:
SNS_TOPIC_ARN_EVENT: The topic to send docdb events.    

S3 target environment variables:
BUCKET_NAME: The name of the bucket that will save streamed data. 
BUCKET_PATH (optional): The path of the bucket that will save streamed data. 

ElasticSearch target environment variables:
ELASTICSEARCH_URI: The URI of the Elasticsearch domain where data should be streamed.

Kinesis target environment variables:
KINESIS_STREAM : The Kinesis Stream name to publish DocumentDB events.

SQS target environment variables:
SQS_QUERY_URL: The URL of the Amazon SQS queue to which a message is sent.

"""

db_client = None                        # DocumentDB client - used as source 
kafka_client = None                     # Kafka client - used as target                                            
es_client = None                        # ElasticSearch client - used as target 
kinesis_client = None                   # Kinesis client - used as target 
s3_client = None                        # S3 client - used as target        
sqs_client = None                       # SQS client - used as target                                                   
sns_client = boto3.client('sns')        # SNS client - for exception alerting purposes
clientS3 = boto3.resource('s3')         # S3 client - used to get the DocumentDB certificates
                                  
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# The error code returned when data for the requested resume token has been deleted
TOKEN_DATA_DELETED_CODE = 136


def get_credentials():
    """Retrieve credentials from the Secrets Manager service."""
    boto_session = boto3.session.Session()

    try:
        secret_name = os.environ['DOCUMENTDB_SECRET']

        logger.debug('Retrieving secret {} from Secrets Manger.'.format(secret_name))

        secrets_client = boto_session.client(service_name='secretsmanager',
                                             region_name=boto_session.region_name)
        secret_value = secrets_client.get_secret_value(SecretId=secret_name)

        secret = secret_value['SecretString']
        secret_json = json.loads(secret)
        username = secret_json['username']
        password = secret_json['password']

        logger.debug('Secret {} retrieved from Secrets Manger.'.format(secret_name))

        return (username, password)

    except Exception as ex:
        logger.error('Failed to retrieve secret {}'.format(secret_name))
        raise


def get_db_client():
    """Return an authenticated connection to DocumentDB"""
    # Use a global variable so Lambda can reuse the persisted client on future invocations
    global db_client

    if db_client is None:
        logger.debug('Creating new DocumentDB client.')

        try:
            cluster_uri = os.environ['DOCUMENTDB_URI']
            (username, password) = get_credentials()                   
            db_client = MongoClient(cluster_uri, ssl=True, retryWrites=False, ssl_ca_certs='/tmp/rds-combined-ca-bundle.pem')
            # force the client to connect
            db_client.admin.command('ismaster')
            db_client["admin"].authenticate(name=username, password=password)

            logger.debug('Successfully created new DocumentDB client.')
        except Exception as ex:
            logger.error('Failed to create new DocumentDB client: {}'.format(ex))
            send_sns_alert(str(ex))
            raise

    return db_client


def get_state_collection_client():
    """Return a DocumentDB client for the collection in which we store processing state."""

    logger.debug('Creating state_collection_client.')
    try:
        db_client = get_db_client()
        state_db_name = os.environ['STATE_DB']
        state_collection_name = os.environ['STATE_COLLECTION']
        state_collection = db_client[state_db_name][state_collection_name]
    except Exception as ex:
        logger.error('Failed to create new state collection client: {}'.format(ex))
        send_sns_alert(str(ex))
        raise

    return state_collection


def get_last_processed_id():
    """Return the resume token corresponding to the last successfully processed change event."""
    last_processed_id = None
    logger.debug('Returning last processed id.')
    try:
        state_collection = get_state_collection_client()
        if "WATCHED_COLLECTION_NAME" in os.environ:
            state_doc = state_collection.find_one({'currentState': True, 'dbWatched': str(os.environ['WATCHED_DB_NAME']), 
                'collectionWatched': str(os.environ['WATCHED_COLLECTION_NAME']), 'db_level': False})
        else:
            state_doc = state_collection.find_one({'currentState': True, 'db_level': True, 
                'dbWatched': str(os.environ['WATCHED_DB_NAME'])})
           
        if state_doc is not None:
            if 'lastProcessed' in state_doc: 
                last_processed_id = state_doc['lastProcessed']
        else:
            if "WATCHED_COLLECTION_NAME" in os.environ:
                state_collection.insert_one({'dbWatched': str(os.environ['WATCHED_DB_NAME']),
                    'collectionWatched': str(os.environ['WATCHED_COLLECTION_NAME']), 'currentState': True, 'db_level': False})
            else:
                state_collection.insert_one({'dbWatched': str(os.environ['WATCHED_DB_NAME']), 'currentState': True, 
                    'db_level': True})

    except Exception as ex:
        logger.error('Failed to return last processed id: {}'.format(ex))
        send_sns_alert(str(ex))
        raise

    return last_processed_id


def store_last_processed_id(resume_token):
    """Store the resume token corresponding to the last successfully processed change event."""

    logger.debug('Storing last processed id.')
    try:
        state_collection = get_state_collection_client()
        if "WATCHED_COLLECTION_NAME" in os.environ:
            state_collection.update_one({'dbWatched': str(os.environ['WATCHED_DB_NAME']), 
                'collectionWatched': str(os.environ['WATCHED_COLLECTION_NAME'])},{'$set': {'lastProcessed': resume_token}})
        else:
            state_collection.update_one({'dbWatched': str(os.environ['WATCHED_DB_NAME']), 'db_level': True, },
                {'$set': {'lastProcessed': resume_token}})

    except Exception as ex:
        logger.error('Failed to store last processed id: {}'.format(ex))
        send_sns_alert(str(ex))
        raise


def connect_kafka_producer():
    """Return a MSK client to publish the streaming messages."""
    # Use a global variable so Lambda can reuse the persisted client on future invocations
    global kafka_client
    
    if kafka_client is None:
        logger.debug('Creating new Kafka client.')

        try:
            kafka_client = KafkaProducer(bootstrap_servers=os.environ['MSK_BOOTSTRAP_SRV'])
        except Exception as ex:
            logger.error('Failed to create new Kafka client: {}'.format(ex))
            send_sns_alert(str(ex))
            raise
    
    return kafka_client


def publish_message(producer_instance, topic_name, key, value):
    """Publish documentdb changes to MSK."""
    
    try:
        logger.debug('Publishing message ' + key + ' to Kafka.')
        key_bytes = bytes(key, encoding='utf-8')
        value_bytes = bytes(value, encoding='utf-8')
        producer_instance.send(topic_name, key=key_bytes, value=value_bytes)
        producer_instance.flush()
    except Exception as ex:
        logger.error('Exception in publishing message: {}'.format(ex))
        send_sns_alert(str(ex))
        raise


def get_es_client():
    """Return an Elasticsearch client."""
    
    global es_client
    
    if es_client is None:
        logger.debug('Creating Elasticsearch client Amazon root CA')
        """
            Important:
            Use the following method if you Lambda has access to the Internet, 
            otherwise include the certificate within the package. 

            Comment following line if certificate is loaded it as part of the function. 
        """
        get_es_certificate()                                 

        try:
            es_uri = os.environ['ELASTICSEARCH_URI']
            es_client = Elasticsearch([es_uri],
                                      use_ssl=True,
                                      ca_certs='/tmp/AmazonRootCA1.pem')
        except Exception as ex:
            logger.error('Failed to create new Elasticsearch client: {}'.format(ex))
            send_sns_alert(str(ex))
            raise

    return es_client


def get_es_certificate():                           
    """Gets the certificate to connect to ES."""
    try:
        logger.debug('Getting Amazon Root CA certificate.')
        url = 'https://www.amazontrust.com/repository/AmazonRootCA1.pem'
        urllib.request.urlretrieve(url, '/tmp/AmazonRootCA1.pem')
    except Exception as ex:
        logger.error('Failed to download certificate to connect to ES: {}'.format(ex))
        send_sns_alert(str(ex))
        raise


def send_sns_alert(message):
    """send an SNS alert"""
    try:
        logger.debug('Sending SNS alert.')
        response = sns_client.publish(
            TopicArn=os.environ['SNS_TOPIC_ARN_ALERT'],
            Message=message,
            Subject='Document DB Replication Alarm',
            MessageStructure='default'
        )
    except Exception as ex:
        logger.error('Exception in publishing alert to SNS: {}'.format(ex))
        send_sns_alert(str(ex))
        raise


def publish_sns_event(message):
    """send event to SNS"""
    try:
        logger.debug('Sending SNS message event.')
        response = sns_client.publish(
            TopicArn=os.environ['SNS_TOPIC_ARN_EVENT'],
            Message=message
        )
    except Exception as ex:
        logger.error('Exception in publishing message to SNS: {}'.format(ex))
        send_sns_alert(str(ex))
        raise


def publish_kinesis_event(pkey,message):
    """send event to Kinesis"""
    # Use a global variable so Lambda can reuse the persisted client on future invocations
    global kinesis_client

    if kinesis_client is None:
        logger.debug('Creating new Kinesis client.')
        kinesis_client = boto3.client('kinesis')  

    try:
        logger.debug('Publishing message' + pkey + 'to Kinesis.')
        message_bytes = bytes(message, encoding='utf-8')
        response = kinesis_client.put_record(
            StreamName=os.environ['KINESIS_STREAM'],
            Data=message_bytes,
            PartitionKey=pkey
        )
    except Exception as ex:
        logger.error('Exception in publishing message to Kinesis: {}'.format(ex))
        send_sns_alert(str(ex))
        raise


def getDocDbCertificate():
    """download the current docdb certificate"""
    try:
        logger.debug('Getting DocumentDB certificate from S3.')
        clientS3.Bucket('rds-downloads').download_file('rds-combined-ca-bundle.pem', '/tmp/rds-combined-ca-bundle.pem')
    except Exception as ex:
        logger.error('Exception in publishing message to Kinesis: {}'.format(ex))
        send_sns_alert(str(ex))
        raise


def insertCanary():
    """Inserts a canary event for change stream activation"""
    
    canary_record = None

    try:
        logger.debug('Inserting canary.')
        db_client = get_db_client()
        watched_db = os.environ['WATCHED_DB_NAME']

        if "WATCHED_COLLECTION_NAME" in os.environ:
            watched_collection = os.environ['WATCHED_COLLECTION_NAME']
        else:
            watched_collection = 'canary-collection'

        collection_client = db_client[watched_db][watched_collection]

        canary_record = collection_client.insert_one({ "op_canary": "canary" })
        logger.debug('Canary inserted.')

    except Exception as ex:
        logger.error('Exception in inserting canary: {}'.format(ex))
        send_sns_alert(str(ex))
        raise

    return canary_record


def deleteCanary():
    """Deletes a canary event for change stream activation"""
    
    try:
        logger.debug('Deleting canary.')
        db_client = get_db_client()
        watched_db = os.environ['WATCHED_DB_NAME']

        if "WATCHED_COLLECTION_NAME" in os.environ:
            watched_collection = os.environ['WATCHED_COLLECTION_NAME']
        else:
            watched_collection = 'canary-collection'

        collection_client = db_client[watched_db][watched_collection]
        collection_client.delete_one({ "op_canary": "canary" })
        logger.debug('Canary deleted.')
    
    except Exception as ex:
        logger.error('Exception in deleting canary: {}'.format(ex))
        send_sns_alert(str(ex))
        raise


def publish_sqs_event(pkey,message,order):
    """send event to SQS"""
    # Use a global variable so Lambda can reuse the persisted client on future invocations
    global sqs_client

    if sqs_client is None:
        logger.debug('Creating new SQS client.')
        sqs_client = boto3.client('sqs')  

    try:
        logger.debug('Publishing message to SQS.')
        response = sqs_client.send_message(
            QueueUrl=os.environ['SQS_QUERY_URL'],
            MessageBody=message,
            MessageDeduplicationId=pkey,
            MessageGroupId=order
        )
    except Exception as ex:
        logger.error('Exception in publishing message to SQS: {}'.format(ex))
        send_sns_alert(str(ex))
        raise


def put_s3_event(event, database, collection, doc_id):
    """send event to S3"""
    # Use a global variable so Lambda can reuse the persisted client on future invocations
    global s3_client

    if s3_client is None:
        logger.debug('Creating new S3 client.')
        s3_client = boto3.resource('s3')  

    try:
        logger.debug('Publishing message to S3.') #, str(os.environ['BUCKET_PATH'])
        if "BUCKET_PATH" in os.environ:
            s3_client.Object(os.environ['BUCKET_NAME'], str(os.environ['BUCKET_PATH']) + '/' + database + '/' +
                collection + '/' + datetime.datetime.now().strftime('%Y/%m/%d/') + doc_id).put(Body=event)
        else: 
            s3_client.Object(os.environ['BUCKET_NAME'], database + '/' + collection + '/' + 
                datetime.datetime.now().strftime('%Y/%m/%d/') + doc_id).put(Body=event)

    except Exception as ex:
        logger.error('Exception in publishing message to S3: {}'.format(ex))
        send_sns_alert(str(ex))
        raise

def lambda_handler(event, context):
    """Read any new events from DocumentDB and apply them to an streaming/datastore endpoint."""
    
    events_processed = 0
    canary_record = None
    watcher = None
    folder = None
    filename = None
    kafka_client = None
    getDocDbCertificate()

    try:
        
        # Kafka client set up    
        if "MSK_BOOTSTRAP_SRV" in os.environ:
            kafka_client = connect_kafka_producer()  
            logger.debug('Kafka client set up.')    

        # ElasticSearch target indext set up
        if "ELASTICSEARCH_URI" in os.environ:
            es_client = get_es_client()
            logger.debug('ES client set up.')

        # DocumentDB watched collection set up
        db_client = get_db_client()
        watched_db = os.environ['WATCHED_DB_NAME']
        if "WATCHED_COLLECTION_NAME" in os.environ:
            watched_collection = os.environ['WATCHED_COLLECTION_NAME']
            watcher = db_client[watched_db][watched_collection]
        else: 
            watcher = db_client[watched_db]
        logger.debug('Watching collection {}'.format(watcher))

        # DocumentDB sync set up
        state_sync_count = int(os.environ['Iterations_per_sync'])
        last_processed_id = get_last_processed_id()
        logger.debug("last_processed_id: {}".format(last_processed_id))

        with watcher.watch(full_document='updateLookup', resume_after=last_processed_id) as change_stream:
            i = 0

            if last_processed_id is None:
                canary_record = insertCanary()
                deleteCanary()

            while change_stream.alive and i < int(os.environ['Documents_per_run']):
            
                i += 1
                change_event = change_stream.try_next()
                logger.debug('Event: {}'.format(change_event))
                
                if last_processed_id is None:
                    if change_event['operationType'] == 'delete':
                        store_last_processed_id(change_stream.resume_token)
                        last_processed_id = change_event['_id']['_data']
                    continue
                
                if change_event is None:
                        break
                else:
                    op_type = change_event['operationType']
                    op_id = change_event['_id']['_data']

                    if op_type in ['insert', 'update']:             
                        doc_body = change_event['fullDocument']
                        doc_id = str(doc_body.pop("_id", None))
                        readable = datetime.datetime.fromtimestamp(change_event['clusterTime'].time).isoformat()
                        ######## Uncomment the following line if you want to add operation metadata fields to the document event. 
                        #doc_body.update({'operation':op_type,'timestamp':str(change_event['clusterTime'].time),'timestampReadable':str(readable)})
                        ######## Uncomment the following line if you want to add db and coll metadata fields to the document event. 
                        #doc_body.update({'db':str(change_event['ns']['db']),'coll':str(change_event['ns']['coll'])})
                        payload = {'_id':doc_id}
                        payload.update(doc_body)

                        # Publish event to ES 
                        if "ELASTICSEARCH_URI" in os.environ:
                            es_index = str(change_event['ns']['db']) + '-' + str(change_event['ns']['coll'])
                            es_client.index(index=es_index,id=doc_id,body=json_util.dumps(doc_body))   

                        # Append event for S3 
                        if "BUCKET_NAME" in os.environ:
                            put_s3_event(json_util.dumps(payload), str(change_event['ns']['db']), str(change_event['ns']['coll']),op_id)
                        
                        # Publish event to Kinesis
                        if "KINESIS_STREAM" in os.environ:
                            publish_kinesis_event(str(op_id),json_util.dumps(payload))

                        # Publish event to MSK
                        if "MSK_BOOTSTRAP_SRV" in os.environ:
                            kafka_topic = str(change_event['ns']['db']) + '-' + str(change_event['ns']['coll'])
                            publish_message(kafka_client, kafka_topic, op_id, json_util.dumps(payload))

                        # Publish event to SNS                      # It should be used for FIFO SNS
                        #if "SNS_TOPIC_ARN_EVENT" in os.environ:
                        #    publish_sns_event(json_util.dumps(payload))

                        # Publish event to SQS
                        if "SQS_QUERY_URL" in os.environ:
                            order = str(change_event['ns']['db']) + '-' + str(change_event['ns']['coll'])
                            publish_sqs_event(str(op_id),json_util.dumps(payload),order)

                        logger.debug('Processed event ID {}'.format(op_id))

                    if op_type == 'delete':
                        doc_id = str(change_event['documentKey']['_id'])
                        readable = datetime.datetime.fromtimestamp(change_event['clusterTime'].time).isoformat()
                        payload = {'_id':doc_id}
                        ######## Uncomment the following line if you want to add operation metadata fields to the document event. 
                        #payload.update({'operation':op_type,'timestamp':str(change_event['clusterTime'].time),'timestampReadable':str(readable)})
                        ######## Uncomment the following line if you want to add db and coll metadata fields to the document event. 
                        #payload.update({'db':str(change_event['ns']['db']),'coll':str(change_event['ns']['coll'])})

                        # Delete event from ES
                        if "ELASTICSEARCH_URI" in os.environ:
                            es_index = str(change_event['ns']['db']) + '-' + str(change_event['ns']['coll'])
                            es_client.delete(es_index, doc_id)

                        # Append event for S3
                        if "BUCKET_NAME" in os.environ:
                            put_s3_event(json_util.dumps(payload), str(change_event['ns']['db']), str(change_event['ns']['coll']),op_id)

                        # Publish event to Kinesis
                        if "KINESIS_STREAM" in os.environ:
                            publish_kinesis_event(str(op_id),json_util.dumps(payload))

                        # Publish event to MSK
                        if "MSK_BOOTSTRAP_SRV" in os.environ:
                            kafka_topic = str(change_event['ns']['db']) + '-' + str(change_event['ns']['coll'])
                            publish_message(kafka_client, kafka_topic, op_id, json_util.dumps(payload))   

                        # Publish event to SNS                          # It should be used for FIFO SNS
                        #if "SNS_TOPIC_ARN_EVENT" in os.environ:
                        #    publish_sns_event(json_util.dumps(payload))

                        # Publish event to FIFO SQS                            
                        if "SQS_QUERY_URL" in os.environ:
                            order = str(change_event['ns']['db']) + '-' + str(change_event['ns']['coll'])
                            publish_sqs_event(str(op_id),json_util.dumps(payload),order)

                        logger.debug('Processed event ID {}'.format(op_id))

                    events_processed += 1

                    if events_processed >= state_sync_count and "BUCKET_NAME" not in os.environ:
                        # To reduce DocumentDB IO, only persist the stream state every N events
                        store_last_processed_id(change_stream.resume_token)
                        logger.debug('Synced token {} to state collection'.format(change_stream.resume_token))

    except OperationFailure as of:
        send_sns_alert(str(of))
        if of.code == TOKEN_DATA_DELETED_CODE:
            # Data for the last processed ID has been deleted in the change stream,
            # Store the last known good state so our next invocation
            # starts from the most recently available data
            store_last_processed_id(None)
        raise

    except Exception as ex:
        logger.error('Exception in executing replication: {}'.format(ex))
        send_sns_alert(str(ex))
        raise

    else:
        
        if events_processed > 0:

            store_last_processed_id(change_stream.resume_token)
            logger.debug('Synced token {} to state collection'.format(change_stream.resume_token))
            return{
                'statusCode': 200,
                'description': 'Success',
                'detail': json.dumps(str(events_processed)+ ' records processed successfully.')
            }
        else:
            if canary_record is not None:
                return{
                    'statusCode': 202,
                    'description': 'Success',
                    'detail': json.dumps('Canary applied. No records to process.')
                }
            else:
                return{
                    'statusCode': 201,
                    'description': 'Success',
                    'detail': json.dumps('No records to process.')
                }

    finally:

        # Close Kafka client
        if "MSK_BOOTSTRAP_SRV" in os.environ:                                                 
            kafka_client.close()