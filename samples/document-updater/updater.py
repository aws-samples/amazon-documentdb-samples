from datetime import datetime, timedelta
import sys
import random
import json
import pymongo
import time
import threading
import os
import multiprocessing as mp
import argparse
import string
import math


def deleteLog(appConfig):
    if os.path.exists(appConfig['logFileName']):
        os.remove(appConfig['logFileName'])


def cleanup(appConfig):
    databaseName = appConfig['databaseName']
    collectionName = appConfig['collectionName']
    client = pymongo.MongoClient(appConfig['uri'])
    db = client[databaseName]
    adminDb = client['admin']
    nameSpace = "{}.{}".format(databaseName,collectionName)

    # change streams
    if appConfig['changeStream']:
        printLog("Disabling change streams on {}".format(nameSpace),appConfig)
        adminDb.command({'modifyChangeStreams':1,'enable':False,'database':databaseName,'collection':collectionName})

    client.close()


def setup(appConfig):
    databaseName = appConfig['databaseName']
    collectionName = appConfig['collectionName']

    client = pymongo.MongoClient(appConfig['uri'])
    db = client[databaseName]
    adminDb = client['admin']
    col = db[collectionName]
    tracker_db=client['tracker_db']
    tracker_col=db['tracker_col']
    # check if collection exists, check if entry 
    # create indexes - add code to check if already exists

    list_of_collections = tracker_db.list_collection_names()  # Return a list of collections in 'test_db'
    if db['tracker_col'] in list_of_collections :
          # Check if collection "posts" exists in db (test_db)

    try:
        thisIndexName = 'idx_collectionName_ts'
        printLog("Creating index {}".format(thisIndexName),appConfig)
        col.create_index([('collection_name', pymongo.ASCENDING),('ts', pymongo.ASCENDING)], name=thisIndexName, background=False, unique=False)
    except Exception as e:
        printLog( " Exception during creating index {}".format(str(e)))
 
    first_entry = {
            "collection_name": appConfig['collectionName'],
            "last_scanned_value" : 0,
            "date": datetime.datetime.now(tz=datetime.timezone.utc)
            # scan fields in future, for now we use  _id
            }   
    
      tracker_col.insert(first_entry)  


    nameSpace = "{}.{}".format(databaseName,collectionName)


   
    # create indexes
        
    thisIndexName = 'idx_compressionApplied'
    printLog("Creating index {}".format(thisIndexName),appConfig)
    col.create_index([('compression_applied', pymongo.ASCENDING)], name=thisIndexName, background=False, unique=False)
   
    # let Customer Apply field name - need to be small - fields take space

    # we will need field that doesnt exist ideally, and will never use
        
    # dont apply update if the doc already has the field

    # readme should have alternatives - migarate using dms or mongodump/restore

    # cx can give a _id high watermark

    # custom object _id - needs to comparable

    # just like migration scripts doesnt work if they have mixed data types in _id

    #find the max id 

    db.test_data.find({},{ _id :1}).sort({ _id :-1}).limit(1)

    # get existing count of documents
    numExistingDocuments = col.estimated_document_count()
    if (numExistingDocuments > 0):
        printLog("collection already contains {0} document(s)".format(numExistingDocuments),appConfig)

    client.close()
    
    return numExistingDocuments


def task_worker(threadNum,perfQ,appConfig):
    rateLimit = appConfig['rateLimit']
    runSeconds = appConfig['runSeconds']
    numInsertsPerBatch = appConfig['batchSize']
    numInsertProcesses = appConfig['numInsertProcesses']
    numExistingDocuments = appConfig['numExistingDocuments']
    textSize = appConfig['textSize']
    pctCompressed = appConfig['textCompressible']
    orderedBatches = appConfig['orderedBatches']
    numCustomers = appConfig['numCustomers']
    numProducts = appConfig['numProducts']
    maxQuantity = appConfig['maxQuantity']
    numSecondsDateRange = appConfig['secondsDateRange']
    numOperations = appConfig['numOperations']
    numOperationsThisWorker = math.ceil(numOperations/numInsertProcesses)

    perfReportInterval = 1

    rateLimitPerThread = rateLimit//numInsertProcesses

    numBatchesCompleted = 0

    client = pymongo.MongoClient(appConfig['uri'])
    myDatabaseName = appConfig['databaseName']
    db = client[myDatabaseName]
    myCollectionName = appConfig['collectionName']
    col = db[myCollectionName]

    start = datetime(1980, 1, 1, 1, 1, 1)
    end = datetime(2023, 9, 7, 1, 1, 1)
    
    textValue = "0123456789" * 100
    randomChars = int(textSize * (1 - (pctCompressed / 100)))
    fixedChars = textSize - randomChars
    randomTextBufferSize = 4*1024*1024
    randomTextBufferMaxStart = randomTextBufferSize - fixedChars
    # generate a 4MB random string
    randomString = ''.join(random.choices(string.ascii_uppercase+string.ascii_lowercase,k=4*1024*1024))
    fixedString = "a" * fixedChars

    startTime = time.time()
    nextPerfReportTime = time.time() + perfReportInterval
    intervalSeconds = 2
    nextReportTime = startTime + intervalSeconds
    maxPerInterval = rateLimitPerThread * intervalSeconds

    thisWorkerOps = 0
    thisIntervalOps = 0
    thisBatchInserts = 0
    batchElapsedMs = 0.0
    
    allDone = False

    

    while not allDone:
        # check if we need to slow down

        #start and go through all the docs using _id 
       
        result =  db.test_data.find({_id : { $gte : last_id   }},{ _id :1}).sort({ _id :1}).limit(100)

        #limit skip vs start with an _id


        tracker_col.update( last_scanned_value == last_id where collection_name = "" )
        batchElapsedMs += (time.time() - batchStartTime) * 1000
        numBatchesCompleted += 1
        
        if time.time() > nextPerfReportTime:
            nextPerfReportTime = time.time() + perfReportInterval
            perfQ.put({"name":"batchCompleted","batches":numBatchesCompleted,"latency":batchElapsedMs,"inserts":thisBatchInserts})
            numBatchesCompleted = 0
            batchElapsedMs = 0.0
            thisBatchInserts = 0
            
        if ((time.time() - startTime) >= runSeconds) and (runSeconds > 0):
            allDone = True

        if (thisWorkerOps >= numOperationsThisWorker) and (numOperationsThisWorker > 0):
            allDone = True

        time.sleep(appConfig['waitPeriod']) # need to sleep for slowing down updates?
                
    client.close()
    
    perfQ.put({"name":"processCompleted","processNum":threadNum})


def main():
    parser = argparse.ArgumentParser(description='Data Generator')

    parser.add_argument('--uri',required=True,type=str,help='URI (connection string)')
    parser.add_argument('--processes',required=True,type=int,help='Degree of concurrency')
    parser.add_argument('--database',required=True,type=str,help='Database')
    parser.add_argument('--collection',required=True,type=str,help='Collection')
    parser.add_argument('--batch-size',required=True,type=int,help='Number of documents to read')
    parser.add_argument('--wait-period',required=False,type=int,default=9999999,help='Number of seconds to wait between each batch')

    args = parser.parse_args()
    
    appConfig = {}
    appConfig['uri'] = args.uri
    # appConfig['numInsertProcesses'] = int(args.processes)
    #for now default to one process
    appConfig['numInsertProcesses'] = 1
    appConfig['databaseName'] = args.database
    appConfig['collectionName'] = args.collection
    appConfig['rateLimit'] = int(args.rate_limit)
    appConfig['batchSize'] = int(args.batch_size)
    appConfig['waitPeriod'] = int(args.wait_period)

    
    numExistingDocuments = 0

    random.seed()
    numExistingDocuments = setup(appConfig)
    
    appConfig['numExistingDocuments'] = numExistingDocuments
    
    deleteLog(appConfig)
    
    printLog('---------------------------------------------------------------------------------------',appConfig)
    for thisKey in sorted(appConfig):
        if (thisKey == 'uri'):
            thisUri = appConfig[thisKey]
            thisParsedUri = pymongo.uri_parser.parse_uri(thisUri)
            thisUsername = thisParsedUri['username']
            thisPassword = thisParsedUri['password']
            thisUri = thisUri.replace(thisUsername,'<USERNAME>')
            thisUri = thisUri.replace(thisPassword,'<PASSWORD>')
            printLog("  config | {} | {}".format(thisKey,thisUri),appConfig)
        else:
            printLog("  config | {} | {}".format(thisKey,appConfig[thisKey]),appConfig)
    printLog('---------------------------------------------------------------------------------------',appConfig)
    
    mp.set_start_method('spawn')
    q = mp.Manager().Queue()
    t = threading.Thread(target=reporter,args=(q,appConfig,))
    t.start()
     
    # do we need multi processing or do we want a controlled rate per second on a single thread? how many updateas should we push per second and wait should be handled by customer - depending on whether it is live or offline?

    # if multi processing and trying to go as fast it can - do we run into the chance of 
    # code for higest _id down, so that the old version moves to the right of the heap
    # code for miltuprocessing
    # should we consider document size and try to set max updates per second
    # secondary indexes,I/O optimised

    # wait - wait every x secs after running every y seconds


 
    processList = []
    for loop in range(appConfig['numInsertProcesses']):
        #time.sleep(1)
        p = mp.Process(target=task_worker,args=(loop,q,appConfig))
        processList.append(p)
        
    for process in processList:
        process.start()
        
    for process in processList:
        process.join()
        
    t.join()
    
    reportCollectionInfo(appConfig)

    cleanup(appConfig)
    
    printLog("Created {} and {} with results".format(appConfig['logFileName'],appConfig['csvFileName']),appConfig)


if __name__ == "__main__":
    main()
