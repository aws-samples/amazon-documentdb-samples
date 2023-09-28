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

read = 0
write = 0

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

DB_ENGINE=f"mongodb"
params = {
    "host": config('DOCDB_HOST', "localhost"),
    "database": config('DOCDB_DB', "better_together"),
    "collection": config('DOCDB_COL', "test_data"),
    "user": config('DOCDB_USER', "admin"),
    "password": config('DOCDB_PASS', "secret_password"),
    "port": config('DOCDB_PORT', 27017),
  }

try:
    DOCDB_CONNECT = f"{DB_ENGINE}://{params['user']}:{params['password']}@{params['host']}:{params['port']}/?replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false"
    client = pymongo.MongoClient(DOCDB_CONNECT)
    db = client[params['database']]
    col = db[params['collection']]

    # Find a random document to make sure we can connect and query
    document = col.find_one()
    if document:
       print("Connected to DocumentDB and found a random document")

except Exception as e:
    print("DocumentDB exception occurred")
    print(e)
    exit(1)

# Method to execute queries and collect timing
def metrics_by_time():
    """
    Define a function to run in a thread
    Captures individual quiery execution times and agregates them per second
    """
    global thread_metrics, read

    for q in range(max_queries):
       
        # Generate a random document ID
        document_id = random.randrange(1,500000)
        
        start_time = time.time()
        document = col.find_one({"_id": document_id})
        end_time = time.time()
        read += 1
        # fail safe clause if generated document id is missing from collection
        if not document:
            continue
       
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

print("Reads: " + str(read))
print("Writes: " + str(write))

if not os.path.exists('logs/1'):
   os.makedirs('logs/1')

file_name = f"logs/1/scenario01_DOCDB_{os.getpid()}_{log_ext}.json"

with open(file_name, "w") as f:
    f.write(json.dumps(thread_metrics, indent=2))
print("Use logfile located here: " + file_name + " in Jupyter notebook")
