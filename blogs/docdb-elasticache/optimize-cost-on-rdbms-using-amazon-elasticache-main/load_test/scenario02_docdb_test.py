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
from redis.commands.json.path import Path

cache_hit = 0
cache_miss = 0

# Set the test execution parameters or use defaults
max_threads = 25
if len(sys.argv) > 1:
  max_threads = int(sys.argv[1])

max_queries = 10000
if len(sys.argv) > 2:
  max_queries = int(sys.argv[2])

log_ext = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
if len(sys.argv) > 3:
  log_ext = str(sys.argv[3])

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

    # Create two connections to ElastiCache distribute reads from writes
    # Since EC is configured in cluster mode enabled the single endpoint connection is used
    ec_write = Redis(host=params['ec_host'], port=params['ec_port'], decode_responses=False)
    ec_read = Redis(host=params['ec_host'], port=params['ec_port'], read_from_replicas=True, decode_responses=True)
    print("Connected to ElastiCache")

except Exception as e:
  print("DocumentDB exception occurred")
  print(e)
  exit(1)


def metrics_by_time():
    """
    Define a function to run in a thread
    Captures individual quiery execution times and agregates them per second 
    """
    global thread_metrics, cache_hit, cache_miss

    for q in range(max_queries):
        
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

            # To store document in cache without an expiration time 
            ec_write.set(key, str(document))

            # To store it with an expiration time or 3600 seconds
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

for i in range(max_threads):
    # Create and start a thread
    thread = threading.Thread(target=metrics_by_time)
    threads.append(thread)
    thread.start()

for i, thread in enumerate(threads):
    # Wait for the thread to finish
    thread.join()

print("Cache hists: " + str(cache_hit))
print("Cache misses: " + str(cache_miss))

if not os.path.exists('logs/1'):
   os.makedirs('logs/1')

file_name = f"logs/1/scenario02_DOCDB_{os.getpid()}_{log_ext}.json"
with open(file_name, "w") as f:
    f.write(json.dumps(thread_metrics, indent=2))
print("Logfile located here: " + file_name)
