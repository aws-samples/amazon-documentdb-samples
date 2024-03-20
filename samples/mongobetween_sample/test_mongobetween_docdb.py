import argparse
import sys
import logging
from datetime import datetime
from multiprocessing import Process
import os
import time
import pymongo

def info(title):
    print(title)
    print('module name:', __name__)
    print('parent process:', os.getppid())
    print('process id:', os.getpid())

logging.basicConfig(filename=datetime.now().strftime('logs/mongobetween_test_%H_%M_%d_%m_%Y.log'), level=logging.DEBUG)


def thread_function(process_counter,conn_str,start):
    print("process starting - ", process_counter)
    try:
        client = pymongo.MongoClient(conn_str)
        collection_name = 'mongobetween_test_coll_'+str(process_counter)
        db = client['mongobetween_test_db']
        coll = db.get_collection(collection_name)
        coll.delete_many({})
        for count in range(1000):
            coll.insert_one({"_id":count})
        for count in range(1000):
            coll.find_one({"_id":count})
        end = time.time()
        logging.info("time taken by process {} is {} milliseconds".format(process_counter,round((end - start)*1000)))
    except Exception as e:
        logging.error("exception in mongo client {} : {}".format(process_counter,str(e)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create connections to Amazon DocumentDB cluster .')
    parser.add_argument('--mongo-clients-count', type=int, default=100, help='Number of Mongo Clients to create (optional, default: 100)')
    parser.add_argument('--docdb-uri', type=str, required=True, help='Amazon DocumentDB cluster URI (required)')
    args = parser.parse_args()
    info('main line')
    procs = []

    for i in range(args.mongo_clients_count):
        proc = Process(target=thread_function, args=(i,args.docdb_uri,time.time()))
        procs.append(proc)
        proc.start()
    # complete the processes
    for proc in procs:
        proc.join()
    print("Completed execution of script. Checks logs directory for results.")