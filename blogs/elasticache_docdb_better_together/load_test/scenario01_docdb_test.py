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
import json
import functools
import logging

MAX_AUTO_RECONNECT_ATTEMPTS = 5
read = 0
write = 0

# Set the test execution parameters or use defaults

import argparse
parser = argparse.ArgumentParser(description=f"AWS Samples - Harness test for RDBMS and Cache")
parser.add_argument('--threads', type=int, default=4, help='Number of threads to spawn.')
parser.add_argument('--queries', type=int, default=10, help='Number of queries to be run by each thread.')
parser.add_argument('--read_rate', type=int, default=90, help='Number of queries to be run by each thread.')
parser.add_argument('--log_tag', type=str, help='A unique string to be applided to the logfile.')

args = parser.parse_args()

if not args.log_tag:
    args.log_tag = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

# Adjust read rate to between 0 and 1
args.read_rate = args.read_rate/100

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


def read_write(p):
    return 1 if random.triangular(0, 1, p) < p else 0


# Create a new document with a given document id 
def new_document(doc_id):
    new_doc = {
        "_id" : doc_id,
        "user_id" : "31cd40f5-4595-491a-bf62-50d788c49f8b",
        "created_on" : 1384947582,
        "gender" : "M",
        "full_name" : "Clarence Kowalski",
        "married" : False,
        "address" : {
                "primary" : {
                        "city" : "League City",
                        "cc" : "TP"
                },
                "secondary" : {
                }
        },
        "coordinates" : [
                -40.07258252041687,
                98.87707768660047
        ],
        "children" : [ ],
        "friends" : [
                "1925173a-6b0b-49ca-b1cd-40f54595691a"
        ],
        "debt" : "null"
    }

    return new_doc


def graceful_auto_reconnect(mongo_op_func):
  """Gracefully handle a reconnection event."""
  @functools.wraps(mongo_op_func)
  def wrapper(*args, **kwargs):
    for attempt in range(MAX_AUTO_RECONNECT_ATTEMPTS):
      try:
        return mongo_op_func(*args, **kwargs)
      except pymongo.errors.AutoReconnect as e:
        wait_t = 0.5 * pow(2, attempt) # exponential back off
        logging.warning("PyMongo auto-reconnecting... %s. Waiting %.1f seconds.", str(e), wait_t)
        time.sleep(wait_t)

  return wrapper


@graceful_auto_reconnect
def find_a_document(document_id):
    return col.find_one({"_id": document_id})


@graceful_auto_reconnect
def change_marrital_status(document_id, status):
    return col.find_one_and_update({"_id": document_id},
                         { '$set': { "create_on" : time.time(),
                                     "married"   : status } 
                         })


# Method to execute queries and collect timing
def metrics_by_time():
    """
    Define a function to run in a thread
    Captures individual query execution times and agregates them per second
    """
    global thread_metrics, read, write
    
    for q in range(args.queries):
       
        # Generate a random document ID
        document_id = random.randrange(1,500000)
        
        if read_write(args.read_rate):
           start_time = time.time()
           # document = col.find_one({"_id": document_id})
           document = find_a_document(document_id)
           end_time = time.time()
           read += 1
           # fail safe clause if randomly generated document id is missing from the collection
           if not document:
              continue
        else:
          start_time = time.time()
          # update a random document 
          change_marrital_status(document_id, random.choice([True, False]))

          end_time = time.time()
          write += 1

        query_time = end_time - start_time
        timestamp = str(int(start_time))

        # gather individual command execution metrics and tabulate them 
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

for i in range(args.threads):
    # Create and start a thread
    thread = threading.Thread(target=metrics_by_time)
    threads.append(thread)
    thread.start()

for i, thread in enumerate(threads):
    # Wait for the thread to finish
    thread.join()

print("Reads: " + str(read))
print("Writes: " + str(write))

# save gathered statistics in a file for analytics
if not os.path.exists('logs/1'):
   os.makedirs('logs/1')

file_name = f"logs/1/scenario01_DOCDB_{os.getpid()}_{args.log_tag}.json"

with open(file_name, "w") as f:
    f.write(json.dumps(thread_metrics, indent=2))
print("Use logfile located here: " + file_name + " in Jupyter notebook")
