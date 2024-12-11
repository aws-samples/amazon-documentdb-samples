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
import warnings


def deleteLog(appConfig):
    if os.path.exists(appConfig['logFileName']):
        os.remove(appConfig['logFileName'])


def printLog(thisMessage,appConfig):
    print("{}".format(thisMessage))
    with open(appConfig['logFileName'], 'a') as fp:
        fp.write("{}\n".format(thisMessage))


def deleteCsv(appConfig):
    if os.path.exists(appConfig['csvFileName']):
        os.remove(appConfig['csvFileName'])


def printCsv(thisMessage,appConfig):
    with open(appConfig['csvFileName'], 'a') as fp:
        fp.write("{}\n".format(thisMessage))


def reportCollectionInfo(appConfig):
    client = pymongo.MongoClient(appConfig['uri'])
    db = client[appConfig['databaseName']]
    
    collStats = db.command("collStats", appConfig['collectionName'])
    
    compressionRatio = collStats['size'] / collStats['storageSize']
    gbDivisor = 1024*1024*1024
    
    printLog("collection statistics | numDocs             = {0:12,d}".format(collStats['count']),appConfig)
    printLog("collection statistics | avgObjSize          = {0:12,d}".format(int(collStats['avgObjSize'])),appConfig)
    printLog("collection statistics | size (GB)           = {0:12,.4f}".format(collStats['size']/gbDivisor),appConfig)
    printLog("collection statistics | storageSize (GB)    = {0:12,.4f} ".format(collStats['storageSize']/gbDivisor),appConfig)
    printLog("collection statistics | compressionRatio    = {0:12,.4f}".format(compressionRatio),appConfig)
    printLog("collection statistics | totalIndexSize (GB) = {0:12,.4f}".format(collStats['totalIndexSize']/gbDivisor),appConfig)
    
    client.close()


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
    numSecondaryIndexes = appConfig['numSecondaryIndexes']

    client = pymongo.MongoClient(appConfig['uri'])
    db = client[databaseName]
    adminDb = client['admin']
    col = db[collectionName]
    nameSpace = "{}.{}".format(databaseName,collectionName)

    if appConfig['dropCollection']:
        printLog("Dropping collection {}".format(nameSpace),appConfig)
        startTime = time.time()
        col.drop()
        elapsedMs = int((time.time() - startTime) * 1000)
        printLog("  completed in {} ms".format(elapsedMs),appConfig)
        
        if appConfig['shard']:
            # sharded
            printLog("Creating sharded collection {}".format(nameSpace),appConfig)
            startTime = time.time()
            db.command({'shardCollection':nameSpace,'key':{'customerId':'hashed'}})
            elapsedMs = int((time.time() - startTime) * 1000)
            printLog("  completed in {} ms".format(elapsedMs),appConfig)
        else:
            # not sharded
            if appConfig['compress']:
                printLog("Creating compressed collection {}".format(nameSpace),appConfig)
                startTime = time.time()
                db.create_collection(name=collectionName,storageEngine={"documentDB":{"compression":{"enable":True}}})
                elapsedMs = int((time.time() - startTime) * 1000)
                printLog("  completed in {} ms".format(elapsedMs),appConfig)
            else:
                printLog("Creating uncompressed collection {}".format(nameSpace),appConfig)
                startTime = time.time()
                db.create_collection(name=collectionName)
                elapsedMs = int((time.time() - startTime) * 1000)
                printLog("  completed in {} ms".format(elapsedMs),appConfig)
    
        # create indexes
        if numSecondaryIndexes >= 1:
            thisIndexName = 'idx_customerId_orderDate'
            printLog("Creating index {}".format(thisIndexName),appConfig)
            col.create_index([('customerId', pymongo.ASCENDING),('orderDate', pymongo.ASCENDING)], name=thisIndexName, background=False, unique=False)

        if numSecondaryIndexes >= 2:
            thisIndexName = 'idx_customerId_productId'
            printLog("Creating index {}".format(thisIndexName),appConfig)
            col.create_index([('customerId', pymongo.ASCENDING),('productId', pymongo.ASCENDING)], name=thisIndexName, background=False, unique=False)

        if numSecondaryIndexes >= 3:
            thisIndexName = 'idx_productId_orderDate'
            printLog("Creating index {}".format(thisIndexName),appConfig)
            col.create_index([('productId', pymongo.ASCENDING),('orderDate', pymongo.ASCENDING)], name=thisIndexName, background=False, unique=False)

    # change streams
    if appConfig['changeStream']:
        printLog("Enabling change streams on {}".format(nameSpace),appConfig)
        adminDb.command({'modifyChangeStreams':1,'enable':True,'database':databaseName,'collection':collectionName})

    # get existing count of documents
    numExistingDocuments = col.estimated_document_count()
    if (numExistingDocuments > 0):
        printLog("collection already contains {0} document(s)".format(numExistingDocuments),appConfig)

    client.close()
    
    return numExistingDocuments


def reporter(perfQ,appConfig):
    numSecondsFeedback = 10
    numIntervalsTps = appConfig['numIntervalsAverage'] 
    numInsertProcesses = appConfig['numInsertProcesses']
    numExistingDocuments = appConfig['numExistingDocuments']
    numOperations = appConfig['numOperations']
    runSeconds = appConfig['runSeconds']

    startTime = time.time()
    lastTime = time.time()
    numTotalInserts = 0
    lastNumTotalInserts = 0
    nextReportTime = startTime + numSecondsFeedback
    intervalLatencyMs = 0
    
    numThreadsCompleted = 0
    recentTps = []
    recentLatency = []
    
    csvHeader = "timestamp,elapsed-time,elapsed-seconds,inserts,overall-ips,total-documents,this-interval-ips,this-interval-latency-ms,last-{}-intervals-ips,last-{}-intervals-latency-ms".format(numIntervalsTps,numIntervalsTps)
    printCsv(csvHeader,appConfig)
    
    while (numThreadsCompleted < numInsertProcesses):
        time.sleep(numSecondsFeedback)
        nowTime = time.time()
        
        numLatencyBatches = 0
        numLatencyMs = 0.0
        
        while not perfQ.empty():
            qMessage = perfQ.get_nowait()
            if qMessage['name'] == "batchCompleted":
                numLatencyBatches += qMessage['batches']
                numLatencyMs += qMessage['latency']
                numTotalInserts += qMessage['inserts']
            elif qMessage['name'] == "processCompleted":
                numThreadsCompleted += 1

        # total total
        elapsedSeconds = nowTime - startTime
        insertsPerSecond = numTotalInserts / elapsedSeconds

        # elapsed hours, minutes, seconds
        thisHours, rem = divmod(elapsedSeconds, 3600)
        thisMinutes, thisSeconds = divmod(rem, 60)
        thisHMS = "{:0>2}:{:0>2}:{:05.2f}".format(int(thisHours),int(thisMinutes),thisSeconds)
        
        # this interval
        intervalElapsedSeconds = nowTime - lastTime
        intervalInserts = numTotalInserts - lastNumTotalInserts
        intervalInsertsPerSecond = intervalInserts / intervalElapsedSeconds
        if numLatencyBatches > 0:
            intervalLatencyMs = numLatencyMs / numLatencyBatches
        else:
            intervalLatencyMs = 0.0
        
        # recent intervals - tps
        if len(recentTps) == numIntervalsTps:
            recentTps.pop(0)
        recentTps.append(intervalInsertsPerSecond)
        totRecentTps = 0
        for thisTps in recentTps:
            totRecentTps += thisTps
        avgRecentTps = totRecentTps / len(recentTps)

        # recent intervals - latency 
        if len(recentLatency) == numIntervalsTps:
            recentLatency.pop(0)
        recentLatency.append(intervalLatencyMs)
        totRecentLatency = 0.0
        for thisLatency in recentLatency:
            totRecentLatency += thisLatency
        avgRecentLatency = totRecentLatency / len(recentLatency)

        # estimated time to done
        if numOperations > 0:
            pctDone = numTotalInserts / numOperations
            remainingSeconds = max(int(elapsedSeconds / pctDone) - elapsedSeconds,0)
        else:
            remainingSeconds = max(runSeconds - elapsedSeconds,0)
        thisHours, rem = divmod(remainingSeconds, 3600)
        thisMinutes, thisSeconds = divmod(rem, 60)
        remainHMS = "{:0>2}:{:0>2}:{:0>2}".format(int(thisHours),int(thisMinutes),int(thisSeconds))
        
        logTimeStamp = datetime.utcnow().isoformat()[:-3] + 'Z'
        printLog("[{}] elapsed {} | total ins {:16,d} at {:12,.2f} p/s | tot docs {:16,d} | interval {:12,.2f} p/s @ {:8,.2f} ms | last {} is {:12,.2f} p/s @ {:8,.2f} ms  | done in {}".format(logTimeStamp,thisHMS,numTotalInserts,insertsPerSecond,numTotalInserts+numExistingDocuments,intervalInsertsPerSecond,intervalLatencyMs,numIntervalsTps,avgRecentTps,avgRecentLatency,remainHMS),appConfig)
        csvData = "{},{},{:.2f},{},{:.2f},{},{:.2f},{:.2f},{:.2f},{:.2f}".format(logTimeStamp,thisHMS,elapsedSeconds,numTotalInserts,insertsPerSecond,numTotalInserts+numExistingDocuments,intervalInsertsPerSecond,intervalLatencyMs,avgRecentTps,avgRecentLatency)
        printCsv(csvData,appConfig)
        nextReportTime = nowTime + numSecondsFeedback
        
        lastTime = nowTime
        lastNumTotalInserts = numTotalInserts


def task_worker(threadNum,perfQ,appConfig):
    warnings.filterwarnings("ignore","You appear to be connected to a DocumentDB cluster.")

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
        if time.time() > nextReportTime:
            # we are running slower than the rate limiter
            nextReportTime = time.time() + intervalSeconds
            thisIntervalOps = 0
        elif thisIntervalOps >= maxPerInterval:
            # slow down
            sleepTimeSeconds = nextReportTime - time.time()
            #printLog("RATE LIMITING : sleeping for {:8,.3f} seconds".format(sleepTimeSeconds),appConfig)
            time.sleep(sleepTimeSeconds)
            nextReportTime = time.time() + intervalSeconds
            thisIntervalOps = 0

        insList = []
        
        for batchLoop in range(numInsertsPerBatch):
            thisInsert = {}
            
            thisTimestamp = datetime.utcnow()
            thisInsert["customerId"] = random.randint(1,numCustomers)
            thisInsert["productId"] = random.randint(1,numProducts)
            thisInsert["quantity"] = random.randint(1,maxQuantity)
            thisInsert["orderDate"] = datetime.utcnow()-timedelta(seconds=numSecondsDateRange)

            randomStringStart = random.randint(1,randomTextBufferMaxStart)-1
            thisInsert["textField"] = randomString[randomStringStart:randomStringStart+randomChars]+fixedString
            
            insList.append(pymongo.InsertOne(thisInsert))
            
            thisBatchInserts += 1
            thisIntervalOps += 1
            thisWorkerOps += 1
        
        batchStartTime = time.time()
        result = col.bulk_write(insList, ordered=orderedBatches)
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
        
    client.close()
    
    perfQ.put({"name":"processCompleted","processNum":threadNum})


def main():
    warnings.filterwarnings("ignore","You appear to be connected to a DocumentDB cluster.")

    parser = argparse.ArgumentParser(description='Data Generator')

    parser.add_argument('--uri',required=True,type=str,help='URI (connection string)')
    parser.add_argument('--processes',required=True,type=int,help='Degree of concurrency')
    parser.add_argument('--database',required=True,type=str,help='Database')
    parser.add_argument('--collection',required=True,type=str,help='Collection')
    parser.add_argument('--run-seconds',required=False,type=int,default=0,help='Total number of seconds to run for')
    parser.add_argument('--num-operations',required=False,type=int,default=0,help='Total number of operations to run for')
    parser.add_argument('--batch-size',required=True,type=int,help='Number of documents to insert per batch')
    parser.add_argument('--rate-limit',required=False,type=int,default=9999999,help='Limit throughput (operations per second)')
    parser.add_argument('--text-size',required=False,type=int,default=1024,help='Size of text field (bytes)')
    parser.add_argument('--text-compressible',required=False,type=int,default=25,help='Compressibility of text field (percentage)')
    parser.add_argument('--ordered-batches',required=False,action='store_true',help='Use ordered bulk-writes')
    parser.add_argument('--drop-collection',required=False,action='store_true',help='Drop the collection (if it exists)')
    parser.add_argument('--compress',required=False,action='store_true',help='Compress the collection')
    parser.add_argument('--shard',required=False,action='store_true',help='Shard the collection')
    parser.add_argument('--num-customers',required=False,type=int,default=10000,help='Number of customers')
    parser.add_argument('--num-products',required=False,type=int,default=1000000,help='Number of products')
    parser.add_argument('--max-quantity',required=False,type=int,default=100000,help='Maximum quantity')
    parser.add_argument('--seconds-date-range',required=False,type=int,default=87400*90,help='Number of seconds for range of orderDate field')
    parser.add_argument('--num-secondary-indexes',required=False,type=int,default=3,choices=[0,1,2,3],help='Number of secondary indexes')
    parser.add_argument('--file-name',required=False,type=str,default='benchmark',help='Starting name of the created CSV and log files')
    parser.add_argument('--change-stream',required=False,action='store_true',help='Enable change streams')
    parser.add_argument('--num-intervals-average',required=False,type=int,default=10,help='Number of intervals for averaging')

    args = parser.parse_args()
    
    if args.compress and not args.drop_collection:
        printLog("Collection must be dropped to enable compression, add --drop-collection",appConfig)
        sys.exit(1)

    if args.shard and not args.drop_collection:
        printLog("Collection must be dropped to enable sharding, add --drop-collection",appConfig)
        sys.exit(1)

    if args.shard and args.change_stream:
        printLog("Change streams are not currently supported on sharded collections",appConfig)
        sys.exit(1)

    appConfig = {}
    appConfig['uri'] = args.uri
    appConfig['numInsertProcesses'] = int(args.processes)
    appConfig['databaseName'] = args.database
    appConfig['collectionName'] = args.collection
    appConfig['runSeconds'] = int(args.run_seconds)
    appConfig['numOperations'] = int(args.num_operations)
    appConfig['rateLimit'] = int(args.rate_limit)
    appConfig['batchSize'] = int(args.batch_size)
    appConfig['textSize'] = int(args.text_size)
    appConfig['textCompressible'] = int(args.text_compressible)
    appConfig['orderedBatches'] = args.ordered_batches
    appConfig['dropCollection'] = args.drop_collection
    appConfig['compress'] = args.compress
    appConfig['shard'] = args.shard
    appConfig['numCustomers'] = int(args.num_customers)
    appConfig['numProducts'] = int(args.num_products)
    appConfig['maxQuantity'] = int(args.max_quantity)
    appConfig['secondsDateRange'] = int(args.seconds_date_range)
    appConfig['numSecondaryIndexes'] = int(args.num_secondary_indexes)
    appConfig['logFileName'] = "{}.log".format(args.file_name)
    appConfig['csvFileName'] = "{}.csv".format(args.file_name)
    appConfig['changeStream'] = args.change_stream
    appConfig['numIntervalsAverage'] = int(args.num_intervals_average)

    if (appConfig['runSeconds'] == 0 and appConfig['numOperations'] == 0):
        printLog("Must supply non-zero for one of --run-seconds or --num-operations",appConfig)
        sys.exit(1)

    if (appConfig['runSeconds'] > 0 and appConfig['numOperations'] > 0):
        printLog("Cannot supply non-zero for both --run-seconds and --num-operations",appConfig)
        sys.exit(1)
    
    numExistingDocuments = 0

    random.seed()
    numExistingDocuments = setup(appConfig)
    
    appConfig['numExistingDocuments'] = numExistingDocuments
    
    deleteLog(appConfig)
    deleteCsv(appConfig)
    
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
            if type(appConfig[thisKey]) == int:
                printLog("  config | {} | {:,d}".format(thisKey,appConfig[thisKey]),appConfig)
            else:
                printLog("  config | {} | {}".format(thisKey,appConfig[thisKey]),appConfig)
    printLog('---------------------------------------------------------------------------------------',appConfig)
    
    mp.set_start_method('spawn')
    q = mp.Manager().Queue()
    t = threading.Thread(target=reporter,args=(q,appConfig,))
    t.start()
    
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
