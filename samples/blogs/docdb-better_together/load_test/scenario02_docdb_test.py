import json
import random
import time
import threading
import sys
import os
import logging
from rich import print
from decouple import config
import pymongo
import string
from redis import RedisCluster as Redis
#from redis.commands.json.path import Path

cache_hit = 0
cache_miss = 0

# Set the test execution parameters or use defaults
import argparse
parser = argparse.ArgumentParser(description=f"AWS Samples - Harness test for RDBMS and Cache")
parser.add_argument('--threads', type=int, default=4, help='Number of threads to spawn.')
parser.add_argument('--queries', type=int, default=10, help='Number of queries to be run by each thread.')
# parser.add_argument('--read_rate', type=int, default=80, help='Number of queries to be run by each thread.')
parser.add_argument('--log_tag', type=str, help='A unique string to be applided to the logfile.')

args = parser.parse_args()

if not args.log_tag:
    args.log_tag = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))


# Define a thread-local storage object to hold connections
thread_local = threading.local()

params = {
    "db_host": config('DOCDB_HOST', "localhost"),
    "database": config('DOCDB_DB', "better_together"),
    "collection": config('DOCDB_COL', "test_data"),
    "user": config('DOCDB_USER', "docdbadmin"),
    "password": config('DOCDB_PASS', "randompasswrod"),
    "db_port": config('DOCDB_PORT', 27017),
    "ec_host": config('ELASTICACHE_ENDPOINT', 'localhost'),
    "ec_port": config('ELASTICACHE_PORT', 6379),
  }

try:
    DOCDB_CONNECT = f"mongodb://{params['user']}:{params['password']}@{params['db_host']}:{params['db_port']}/?replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false"
    client = pymongo.MongoClient(DOCDB_CONNECT)
    db = client[params['database']]
    col = db[params['collection']]
    # Find a random document to make sure we can connect and query
    document = col.find_one()

    if document:
       print("Connected to DocumentDB and found a random document")

    # Create two ElastiCache connection to distribute reads from writes
    # Since EC is configured in cluster mode enabled the single endpoint connection is used
    # If encryption in transit is enabled:
    # ec_write = Redis(host=params['ec_host'], port=params['ec_port'], ssl=True, decode_responses=False, socket_connect_timeout = 5)
    # ec_read = Redis(host=params['ec_host'], port=params['ec_port'], ssl=True, read_from_replicas=True, decode_responses=True, socket_connect_timeout = 5)
    # If encryption in transit is not enabled
    ec_write = Redis(host=params['ec_host'], port=params['ec_port'], decode_responses=False, socket_connect_timeout = 5)
    ec_read = Redis(host=params['ec_host'], port=params['ec_port'], read_from_replicas=True, decode_responses=True, socket_connect_timeout = 5)
    print("Connected to ElastiCache")

except Exception as e:
  print("Connection exception occurred")
  print(e)
  exit(1)


def metrics_by_time():
    """
    Define a function to run in a thread
    Captures individual quiery execution times and agregates them per second 
    """
    global thread_metrics, cache_hit, cache_miss

    for q in range(args.queries):
        
        # Generate a random document ID and a key
        document_id = random.randrange(1,500000)
        key = f"tdoc:{document_id}"
        
        start_time = time.time()
        document = ec_read.get(key)
        end_time = time.time()

        # IF we found a document with the key it is a cache hit. NO need to query DocumentDB
        if document: 
            cache_hit += 1

        # IF we found no documnet with the key query as before and save a copy in ElastiCache 
        else:
            start_time = time.time()
            document = col.find_one({"_id": document_id})
            end_time = time.time()

            # Store document in cache without an expiration time 
            ec_write.set(key, str(document))

            # Store it with an expiration time or 3600 seconds
            # ec_write.setex(key, 3600, str(document))

            cache_miss += 1
       
        query_time = end_time - start_time
        timestamp = str(int(start_time))

        if timestamp not in thread_metrics:
            thread_metrics[timestamp] = {
                "count": 1,
                "query_time": query_time,
                "min_time": query_time,
                "max_time": query_time,
             }
        else:
            thread_metrics[timestamp]["count"] += 1
            thread_metrics[timestamp]["query_time"] += query_time
            if query_time < thread_metrics[timestamp]["min_time"]:
                thread_metrics[timestamp]["min_time"] = query_time
            if query_time > thread_metrics[timestamp]["max_time"]:
                thread_metrics[timestamp]["max_time"] = query_time


threads = list()
thread_metrics = dict()

# Hydrate the cache
#missing = 0
#for i in range(500000):
#    key = f"tdoc:{i}"
#    document = ec_read.get(key)
#    if not document: 
#        document = col.find_one({"_id": i})
#        ec_write.set(key, str(document))
#        missing += 1

#print("Missing count: " + str(missing))
#exit(1)

for i in range(args.threads):
    # Create and start a thread
    thread = threading.Thread(target=metrics_by_time)
    threads.append(thread)
    thread.start()

for i, thread in enumerate(threads):
    # Wait for the thread to finish
    thread.join()

print("Cache hits: " + str(cache_hit))
print("Cache misses: " + str(cache_miss))

if not os.path.exists('logs/1'):
   os.makedirs('logs/1')

file_name = f"logs/1/scenario02_DOCDB_{os.getpid()}_{args.log_tag}.json"

with open(file_name, "w") as f:
    f.write(json.dumps(thread_metrics, indent=2))
print("Logfile located here: " + file_name)
