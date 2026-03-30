import datetime as dt
import sys
import random
import json
import pymongo
from pymongo.errors import DuplicateKeyError
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


def sysbench_string(length):
    # generate full string
    digits = ''.join(str(random.randint(0, 9)) for _ in range(length))
    
    # insert dashes every 12 characters
    result = ''
    for i in range(len(digits)):
        if i > 0 and i % 12 == 0:
            result += '-'
        result += digits[i]
    
    return result


def reportCollectionInfo(appConfig):
    numCollections = appConfig['numCollections']
    
    client = pymongo.MongoClient(appConfig['uri'])
    db = client[appConfig['databaseName']]
    
    for thisCollectionNum in range(1,numCollections+1):
        thisCollectionName = "{}{}".format(appConfig['collectionName'],thisCollectionNum)
        
        collStats = db.command("collStats", thisCollectionName)
        
        compressionRatio = collStats['size'] / collStats['storageSize']
        gbDivisor = 1024*1024*1024
        
        printLog("{} ----------------------------------------------------------".format(thisCollectionName),appConfig)
        printLog("collection statistics | numDocs             = {0:14,d}".format(collStats['count']),appConfig)
        printLog("collection statistics | avgObjSize          = {0:14,d}".format(int(collStats['avgObjSize'])),appConfig)
        printLog("collection statistics | size (GB)           = {0:14,.4f}".format(collStats['size']/gbDivisor),appConfig)
        printLog("collection statistics | storageSize (GB)    = {0:14,.4f} ".format(collStats['storageSize']/gbDivisor),appConfig)
        printLog("collection statistics | compressionRatio    = {0:14,.4f}".format(compressionRatio),appConfig)
        printLog("collection statistics | totalIndexSize (GB) = {0:14,.4f}".format(collStats['totalIndexSize']/gbDivisor),appConfig)
    
    client.close()


def reportDatabaseInfo(appConfig):
    client = pymongo.MongoClient(appConfig['uri'])
    db = client[appConfig['databaseName']]

    dbStats = db.command("dbstats")

    gbDivisor = 1024*1024*1024

    printLog("{} ----------------------------------------------------------".format(appConfig['databaseName']),appConfig)
    printLog("database statistics | numDocs           = {0:14,d}".format(dbStats['objects']),appConfig)
    printLog("database statistics | numCollections    = {0:14,d}".format(dbStats['collections']),appConfig)
    printLog("database statistics | numIndexes        = {0:14,d}".format(dbStats['indexes']),appConfig)
    printLog("database statistics | dataSize (GB)     = {0:14,.4f}".format(dbStats['storageSize']/gbDivisor),appConfig)
    printLog("database statistics | indexSize (GB)    = {0:14,.4f} ".format(dbStats['indexSize']/gbDivisor),appConfig)
    printLog("database statistics | totalSize (GB)    = {0:14,.4f}".format(dbStats['fileSize']/gbDivisor),appConfig)
    
    client.close()


def cleanup(appConfig):
    numCollections = appConfig['numCollections']
    databaseName = appConfig['databaseName']
    client = pymongo.MongoClient(appConfig['uri'])
    db = client[databaseName]
    adminDb = client['admin']
    
    for thisCollectionNum in range(1,numCollections+1):
        thisCollectionName = "{}{}".format(appConfig['collectionName'],thisCollectionNum)
    
        nameSpace = "{}.{}".format(databaseName,thisCollectionName)

        # change streams
        if appConfig['changeStream']:
            printLog("Disabling change streams on {}".format(nameSpace),appConfig)
            adminDb.command({'modifyChangeStreams':1,'enable':False,'database':databaseName,'collection':thisCollectionName})

    client.close()


def setup_load(appConfig):
    numCollections = appConfig['numCollections']
    databaseName = appConfig['databaseName']

    client = pymongo.MongoClient(host=appConfig['uri'],appname='pymongosysbench')
    db = client[databaseName]
    adminDb = client['admin']

    for thisCollectionNum in range(1,numCollections+1):
        thisCollectionName = "{}{}".format(appConfig['collectionName'],thisCollectionNum)
    
        col = db[thisCollectionName]
        nameSpace = "{}.{}".format(databaseName,thisCollectionName)

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
            if appConfig['compression'] == 'lz4':
                printLog("Creating lz4 compressed collection {} with threshold 128".format(nameSpace),appConfig)
                startTime = time.time()
                db.create_collection(name=thisCollectionName,storageEngine={"documentDB":{"compression":{"enable":True,"algorithm":"lz4","threshold":128}}})
                elapsedMs = int((time.time() - startTime) * 1000)
                printLog("  completed in {} ms".format(elapsedMs),appConfig)
            elif appConfig['compression'] == 'zstd':
                printLog("Creating zstd compressed collection {}".format(nameSpace),appConfig)
                startTime = time.time()
                db.create_collection(name=thisCollectionName,storageEngine={"documentDB":{"compression":{"enable":True,"algorithm":"zstd"}}})
                elapsedMs = int((time.time() - startTime) * 1000)
                printLog("  completed in {} ms".format(elapsedMs),appConfig)
            elif appConfig['compression'] == 'none':
                printLog("Creating uncompressed collection {}".format(nameSpace),appConfig)
                startTime = time.time()
                db.create_collection(name=thisCollectionName,storageEngine={"documentDB":{"compression":{"enable":False}}})
                elapsedMs = int((time.time() - startTime) * 1000)
                printLog("  completed in {} ms".format(elapsedMs),appConfig)
            elif appConfig['compression'] == 'parmgroup':
                printLog("Creating collection {} using parameter group setting for default_collection_compression choice for compression".format(nameSpace),appConfig)
                startTime = time.time()
                db.create_collection(name=thisCollectionName)
                elapsedMs = int((time.time() - startTime) * 1000)
                printLog("  completed in {} ms".format(elapsedMs),appConfig)
            else:
                printLog("Unknown value {} for --compression, exiting".format(appConfig['compression']))
                sys.exit(1)

        # create secondary indexes
        thisIndexName = 'idx_k'
        printLog("Creating index {}".format(thisIndexName),appConfig)
        col.create_index([('k', pymongo.ASCENDING)], name=thisIndexName, background=False, unique=False)

        # change streams
        if appConfig['changeStream']:
            printLog("Enabling change streams on {}".format(nameSpace),appConfig)
            adminDb.command({'modifyChangeStreams':1,'enable':True,'database':databaseName,'collection':thisCollectionName})

    client.close()
    
    return 0


def setup_run(appConfig):
    numCollections = appConfig['numCollections']
    databaseName = appConfig['databaseName']

    client = pymongo.MongoClient(host=appConfig['uri'],appname='pymongosysbench')
    db = client[databaseName]

    thisCollectionName = "{}{}".format(appConfig['collectionName'],1)
    
    col = db[thisCollectionName]
    nameSpace = "{}.{}".format(databaseName,thisCollectionName)

    # get existing count of documents
    numExistingDocuments = col.estimated_document_count()
    if (numExistingDocuments > 0):
        printLog("collection {} already contains {} document(s)".format(nameSpace,numExistingDocuments),appConfig)

    client.close()
    
    return numExistingDocuments


def reporter(perfQ,appConfig):
    numSecondsFeedback = 10
    numIntervalsTps = appConfig['numIntervalsAverage'] 
    numProcesses = appConfig['numProcesses']
    numExistingDocuments = appConfig['numExistingDocuments']
    runSeconds = appConfig['runSeconds']
    numCollections = appConfig['numCollections']
    numDocumentsPerCollection = appConfig['numDocumentsPerCollection']
    if appConfig['modeLoad']:
        numOperations = numCollections * numDocumentsPerCollection
    else:
        numOperations = appConfig['numOperations']

    startTime = time.time()
    lastTime = time.time()
    numTotalInserts = 0
    numTotalExceptions = 0
    lastNumTotalInserts = 0
    nextReportTime = startTime + numSecondsFeedback
    intervalLatencyMs = 0

    numProcessesCompleted = 0
    recentTps = []
    recentLatency = []
    
    if appConfig['modeLoad']:
        csvHeader = "timestamp,elapsed-time,elapsed-seconds,inserts,overall-ips,this-interval-ips,this-interval-latency-ms,last-{}-intervals-ips,last-{}-intervals-latency-ms,exceptions".format(numIntervalsTps,numIntervalsTps)
    else:
        csvHeader = "timestamp,elapsed-time,elapsed-seconds,transactions,overall-tps,this-interval-tps,this-interval-latency-ms,last-{}-intervals-tps,last-{}-intervals-latency-ms,exceptions".format(numIntervalsTps,numIntervalsTps)
    printCsv(csvHeader,appConfig)
    
    while (numProcessesCompleted < numProcesses):
        time.sleep(numSecondsFeedback)
        nowTime = time.time()
        
        numLatencyBatches = 0
        numLatencyMs = 0.0

        op1Ms = 0.0
        op2Ms = 0.0
        op3Ms = 0.0
        op4Ms = 0.0
        op5Ms = 0.0
        op6Ms = 0.0
        op7Ms = 0.0
        op8Ms = 0.0
        
        while not perfQ.empty():
            qMessage = perfQ.get_nowait()
            if qMessage['name'] == "batchCompleted":
                numLatencyBatches += qMessage['batches']
                numLatencyMs += qMessage['latency']
                numTotalInserts += qMessage['inserts']
                numTotalExceptions += qMessage['exceptions']
            elif qMessage['name'] == "batchDetails":
                op1Ms += qMessage['op1Ms']
                op2Ms += qMessage['op2Ms']
                op3Ms += qMessage['op3Ms']
                op4Ms += qMessage['op4Ms']
                op5Ms += qMessage['op5Ms']
                op6Ms += qMessage['op6Ms']
                op7Ms += qMessage['op7Ms']
                op8Ms += qMessage['op8Ms']
            elif qMessage['name'] == "processCompleted":
                numProcessesCompleted += 1

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
            intervalOp1LatencyMs = op1Ms / numLatencyBatches
            intervalOp2LatencyMs = op2Ms / numLatencyBatches
            intervalOp3LatencyMs = op3Ms / numLatencyBatches
            intervalOp4LatencyMs = op4Ms / numLatencyBatches
            intervalOp5LatencyMs = op5Ms / numLatencyBatches
            intervalOp6LatencyMs = op6Ms / numLatencyBatches
            intervalOp7LatencyMs = op7Ms / numLatencyBatches
            intervalOp8LatencyMs = op8Ms / numLatencyBatches
        else:
            intervalLatencyMs = 0.0
            intervalOp1LatencyMs = 0.0
            intervalOp2LatencyMs = 0.0
            intervalOp3LatencyMs = 0.0
            intervalOp4LatencyMs = 0.0
            intervalOp5LatencyMs = 0.0
            intervalOp6LatencyMs = 0.0
            intervalOp7LatencyMs = 0.0
            intervalOp8LatencyMs = 0.0
        
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
            pctDone = max(numTotalInserts / numOperations,0.001)
            remainingSeconds = max(int(elapsedSeconds / pctDone) - elapsedSeconds,0)
        else:
            remainingSeconds = max(runSeconds - elapsedSeconds,0)
        thisHours, rem = divmod(remainingSeconds, 3600)
        thisMinutes, thisSeconds = divmod(rem, 60)
        remainHMS = "{:0>2}:{:0>2}:{:0>2}".format(int(thisHours),int(thisMinutes),int(thisSeconds))
        
        logTimeStamp = dt.datetime.now(dt.timezone.utc).isoformat()[:-3] + 'Z'
        
        if appConfig['modeLoad']:
            printLog("[{}] elapsed {} | total ins {:12,d} at {:10,.2f} p/s | interval {:10,.2f} p/s @ {:8,.2f} ms | last {} {:10,.2f} p/s @ {:8,.2f} ms | {:6,d} exceptions | ETA {}".format(logTimeStamp,thisHMS,numTotalInserts,insertsPerSecond,intervalInsertsPerSecond,intervalLatencyMs,numIntervalsTps,avgRecentTps,avgRecentLatency,numTotalExceptions,remainHMS),appConfig)
            csvData = "{},{},{:.2f},{},{:.2f},{:.2f},{:.2f},{:.2f},{:.2f},{}".format(logTimeStamp,thisHMS,elapsedSeconds,numTotalInserts,insertsPerSecond,intervalInsertsPerSecond,intervalLatencyMs,avgRecentTps,avgRecentLatency,numTotalExceptions)
        else:
            printLog("[{}] elapsed {} | total txn {:12,d} at {:10,.2f} p/s | interval {:10,.2f} p/s @ {:8,.2f} ms | last {} {:10,.2f} p/s @ {:8,.2f} ms | {:6,d} exceptions | ETA {}".format(logTimeStamp,thisHMS,numTotalInserts,insertsPerSecond,intervalInsertsPerSecond,intervalLatencyMs,numIntervalsTps,avgRecentTps,avgRecentLatency,numTotalExceptions,remainHMS),appConfig)
            if appConfig['showDetailedLatencies']:
                printLog("[1] {:10,.2f} [2] {:10,.2f} [3] {:10,.2f} [4] {:10,.2f} [5] {:10,.2f} [6] {:10,.2f} [7] {:10,.2f} [8] {:10,.2f} ".format(intervalOp1LatencyMs,intervalOp2LatencyMs,intervalOp3LatencyMs,intervalOp4LatencyMs,intervalOp5LatencyMs,intervalOp6LatencyMs,intervalOp7LatencyMs,intervalOp8LatencyMs),appConfig)
            csvData = "{},{},{:.2f},{},{:.2f},{:.2f},{:.2f},{:.2f},{:.2f},{}".format(logTimeStamp,thisHMS,elapsedSeconds,numTotalInserts,insertsPerSecond,intervalInsertsPerSecond,intervalLatencyMs,avgRecentTps,avgRecentLatency,numTotalExceptions)
            
        printCsv(csvData,appConfig)
        nextReportTime = nowTime + numSecondsFeedback
        
        lastTime = nowTime
        lastNumTotalInserts = numTotalInserts


def load_worker(threadNum,perfQ,appConfig):
    warnings.filterwarnings("ignore","You appear to be connected to a DocumentDB cluster.")
    
    random.seed()

    rateLimit = appConfig['rateLimit']
    numDocumentsPerCollection = appConfig['numDocumentsPerCollection']
    numInsertsPerBatch = appConfig['loadBatchSize']
    numProcesses = appConfig['numProcesses']
    orderedBatches = appConfig['orderedBatches']
    padFieldSize = appConfig['padFieldSize']-1
    cFieldSize = appConfig['cFieldSize']-1
    compressibleFieldSize = appConfig['compressibleFieldSize']
    if compressibleFieldSize == 0:
        compressFieldValue = ''
    else:
        compressFieldValue = 'a' * compressibleFieldSize

    perfReportInterval = 1

    rateLimitPerThread = rateLimit//numProcesses

    numBatchesCompleted = 0

    client = pymongo.MongoClient(appConfig['uri'])
    myDatabaseName = appConfig['databaseName']
    db = client[myDatabaseName]
    myCollectionName = "{}{}".format(appConfig['collectionName'],threadNum+1)
    col = db[myCollectionName]

    sysbenchStringBufferSize = 4*1024*1024
    sysbenchString = sysbench_string(sysbenchStringBufferSize)
    textBufferMaxStart = sysbenchStringBufferSize-(1*1024*1024)

    startTime = time.time()
    nextPerfReportTime = time.time() + perfReportInterval
    intervalSeconds = 2
    nextReportTime = startTime + intervalSeconds
    maxPerInterval = rateLimitPerThread * intervalSeconds

    numTotalInserts = 0
    numTotalBatches = 0
    numIntervalInserts = 0
    numIntervalBatches = 0
    numLimiterInserts = 0
    
    batchElapsedMs = 0.0
    
    allDone = False

    while not allDone:
        # check if we need to slow down
        if time.time() > nextReportTime:
            # we are running slower than the rate limiter
            nextReportTime = time.time() + intervalSeconds
            numLimiterInserts = 0
        elif numLimiterInserts >= maxPerInterval:
            # slow down
            sleepTimeSeconds = nextReportTime - time.time()
            #printLog("RATE LIMITING : sleeping for {:8,.3f} seconds".format(sleepTimeSeconds),appConfig)
            time.sleep(sleepTimeSeconds)
            nextReportTime = time.time() + intervalSeconds
            numLimiterInserts = 0

        insList = []
        
        for batchLoop in range(numInsertsPerBatch):
            numTotalInserts += 1
            numIntervalInserts += 1
            numLimiterInserts += 1
            
            thisInsert = {}
            
            thisInsert["_id"] = numTotalInserts
            thisInsert["k"] = numTotalInserts
            # all strings are aligned to 13 so they all start with 12 digits, then dash, then 12 digits, ...
            randomStringStart = round(random.randint(1,textBufferMaxStart)/13)*13
            thisInsert["c"] = sysbenchString[randomStringStart:randomStringStart+cFieldSize]
            randomStringStart = round(random.randint(1,textBufferMaxStart)/13)*13
            thisInsert["pad"] = sysbenchString[randomStringStart:randomStringStart+padFieldSize]
            if compressibleFieldSize > 0:
                thisInsert["compressField"] = compressFieldValue
            thisInsert["numUpdates"] = 0
            
            insList.append(pymongo.InsertOne(thisInsert))
        
        batchStartTime = time.time()
        result = col.bulk_write(insList, ordered=orderedBatches)
        batchElapsedMs += (time.time() - batchStartTime) * 1000
        numTotalBatches += 1
        numIntervalBatches += 1
        
        if time.time() > nextPerfReportTime:
            nextPerfReportTime = time.time() + perfReportInterval
            perfQ.put({"name":"batchCompleted","batches":numIntervalBatches,"latency":batchElapsedMs,"inserts":numIntervalInserts,"exceptions":0})
            numIntervalBatches = 0
            numIntervalInserts = 0
            batchElapsedMs = 0.0
            
        if (numTotalInserts >= numDocumentsPerCollection):
            allDone = True
        
    client.close()
    
    perfQ.put({"name":"processCompleted","processNum":threadNum})


def run_worker(threadNum,perfQ,appConfig):
    warnings.filterwarnings("ignore","You appear to be connected to a DocumentDB cluster.")
    
    random.seed()

    rateLimit = appConfig['rateLimit']
    runSeconds = appConfig['runSeconds']
    numProcesses = appConfig['numProcesses']
    numExistingDocuments = appConfig['numExistingDocuments']
    numOperations = appConfig['numOperations']
    numOperationsThisWorker = math.ceil(numOperations/numProcesses)
    numCollections = appConfig['numCollections']
    padFieldSize = appConfig['padFieldSize']-1
    cFieldSize = appConfig['cFieldSize']-1
    
    sysbenchRangeSize = appConfig['sysbenchRangeSize']
    sysbenchPointQueries = appConfig['sysbenchPointQueries']
    sysbenchSimpleRangeQueries = appConfig['sysbenchSimpleRangeQueries']
    sysbenchSumRangeQueries = appConfig['sysbenchSumRangeQueries']
    sysbenchOrderedRangeQueries = appConfig['sysbenchOrderedRangeQueries']
    sysbenchDistinctRangeQueries = appConfig['sysbenchDistinctRangeQueries']
    sysbenchIndexedUpdates = appConfig['sysbenchIndexedUpdates']
    sysbenchNonIndexedUpdates = appConfig['sysbenchNonIndexedUpdates']
    sysbenchDeletesThenInserts = appConfig['sysbenchDeletesThenInserts']

    indexForQueries = appConfig['indexForQueries']
    if indexForQueries == 'id':
        lookupField = '_id'
    elif indexForQueries == 'k':
        lookupField = 'k'
    else:
        printLog("Unknown value {} for --index-for-queries, exiting".format(indexForQueries))
        sys.exit(1)

    perfReportInterval = 1

    rateLimitPerThread = rateLimit//numProcesses

    numBatchesCompleted = 0

    client = pymongo.MongoClient(appConfig['uri'])
    myDatabaseName = appConfig['databaseName']
    db = client[myDatabaseName]

    sysbenchStringBufferSize = 4*1024*1024
    sysbenchString = sysbench_string(sysbenchStringBufferSize)
    textBufferMaxStart = sysbenchStringBufferSize-(1*1024*1024)

    startTime = time.time()
    nextPerfReportTime = time.time() + perfReportInterval
    intervalSeconds = 2
    nextReportTime = startTime + intervalSeconds
    maxPerInterval = rateLimitPerThread * intervalSeconds

    numTotalOperations = 0
    numTotalTransactions = 0
    numIntervalOperations = 0
    numIntervalTransactions = 0
    numLimiterTransactions = 0
    numTotalExceptions = 0
    numIntervalExceptions = 0

    batchElapsedMs = 0.0

    op1Ms = 0.0
    op2Ms = 0.0
    op3Ms = 0.0
    op4Ms = 0.0
    op5Ms = 0.0
    op6Ms = 0.0
    op7Ms = 0.0
    op8Ms = 0.0

    allDone = False

    while not allDone:
        # check if we need to slow down
        if time.time() > nextReportTime:
            # we are running slower than the rate limiter
            nextReportTime = time.time() + intervalSeconds
            numLimiterTransactions = 0
        elif numLimiterTransactions >= maxPerInterval:
            # slow down
            sleepTimeSeconds = nextReportTime - time.time()
            #printLog("RATE LIMITING : sleeping for {:8,.3f} seconds".format(sleepTimeSeconds),appConfig)
            time.sleep(sleepTimeSeconds)
            nextReportTime = time.time() + intervalSeconds
            numLimiterTransactions = 0
            
        numLimiterTransactions += 1

        # pick the collection
        myCollectionName = "{}{}".format(appConfig['collectionName'],random.randint(1,numCollections))
        col = db[myCollectionName]

        batchStartTime = time.time()

        # point queries
        opStartTime = time.time()
        for loop in range(sysbenchPointQueries):
            numTotalOperations += 1
            numIntervalOperations += 1
            startId = random.randint(1,numExistingDocuments)
            try:
                thisDoc = col.find_one(filter={lookupField:startId},projection={"_id":0,"c":1})
                pass
            except TypeError as e:
                numTotalExceptions += 1
                numIntervalExceptions += 1
        op1Ms += (time.time() - opStartTime) * 1000
    
        # simple ranges
        opStartTime = time.time()
        for loop in range(sysbenchSimpleRangeQueries):
            numTotalOperations += 1
            numIntervalOperations += 1
            startId = random.randint(1,numExistingDocuments)
            endId = startId + sysbenchRangeSize
            for thisDoc in col.find(filter={lookupField:{"$gte":startId,"$lte":endId}},projection={"_id":0,"c":1}):
                pass
        op2Ms += (time.time() - opStartTime) * 1000
        
        # summed ranges
        opStartTime = time.time()
        for loop in range(sysbenchSumRangeQueries):
            numTotalOperations += 1
            numIntervalOperations += 1
            startId = random.randint(1,numExistingDocuments)
            endId = startId + sysbenchRangeSize
            for thisDoc in col.aggregate([{"$match":{lookupField:{"$gte":startId,"$lte":endId}}},{"$project":{"_id":0,"numUpdates":1}},{"$group":{"_id":None,"sum":{"$sum":"$numUpdates"}}}]):
                pass
        op3Ms += (time.time() - opStartTime) * 1000
        
        # ordered ranges
        opStartTime = time.time()
        for loop in range(sysbenchOrderedRangeQueries):
            numTotalOperations += 1
            numIntervalOperations += 1
            startId = random.randint(1,numExistingDocuments)
            endId = startId + sysbenchRangeSize
            for thisDoc in col.find(filter={lookupField:{"$gte":startId,"$lte":endId}},projection={"_id":0,"c":1},sort=[("c",pymongo.ASCENDING)]):
                pass
        op4Ms += (time.time() - opStartTime) * 1000
        
        # distinct ranges
        opStartTime = time.time()
        for loop in range(sysbenchDistinctRangeQueries):
            numTotalOperations += 1
            numIntervalOperations += 1
            startId = random.randint(1,numExistingDocuments)
            endId = startId + sysbenchRangeSize
            for thisDoc in col.distinct("c",filter={lookupField:{"$gte":startId,"$lte":endId}}):
                pass
        op5Ms += (time.time() - opStartTime) * 1000
        
        # indexed updates
        opStartTime = time.time()
        for loop in range(sysbenchIndexedUpdates):
            numTotalOperations += 1
            numIntervalOperations += 1
            startId = random.randint(1,numExistingDocuments)
            newStartId = random.randint(1,numExistingDocuments)
            thisResult = col.update_one({lookupField:startId},{"$set":{"k":newStartId},"$inc":{"numUpdates":1}})
        op6Ms += (time.time() - opStartTime) * 1000
        
        # non-indexed updates
        opStartTime = time.time()
        for loop in range(sysbenchNonIndexedUpdates):
            numTotalOperations += 1
            numIntervalOperations += 1
            startId = random.randint(1,numExistingDocuments)
            randomStringStart = round(random.randint(1,textBufferMaxStart)/13)*13
            thisResult = col.update_one({lookupField:startId},{"$set":{"c":sysbenchString[randomStringStart:randomStringStart+cFieldSize]},"$inc":{"numUpdates":1}})
        op7Ms += (time.time() - opStartTime) * 1000
        
        # deletes then inserts
        opStartTime = time.time()
        for loop in range(sysbenchDeletesThenInserts):
            # increment by two, performing a delete and an insert
            numTotalOperations += 2
            numIntervalOperations += 2
            
            # delete existing document
            startId = random.randint(1,numExistingDocuments)
            thisResult = col.delete_one({"_id":startId})

            # put it back with new values
            thisInsert = {}
            thisInsert["_id"] = startId
            thisInsert["k"] = random.randint(1,numExistingDocuments)
            randomStringStart = round(random.randint(1,textBufferMaxStart)/13)*13
            thisInsert["c"] = sysbenchString[randomStringStart:randomStringStart+cFieldSize]
            randomStringStart = round(random.randint(1,textBufferMaxStart)/13)*13
            thisInsert["pad"] = sysbenchString[randomStringStart:randomStringStart+padFieldSize]
            thisInsert["numUpdates"] = 0
            
            try:
                thisResult = col.insert_one(thisInsert)
            except DuplicateKeyError:
                # race condition - two processes on the same document
                numTotalExceptions += 1
                numIntervalExceptions += 1
        op8Ms += (time.time() - opStartTime) * 1000

        numTotalTransactions += 1
        numIntervalTransactions += 1
        
        batchElapsedMs += (time.time() - batchStartTime) * 1000
        
        if time.time() > nextPerfReportTime:
            nextPerfReportTime = time.time() + perfReportInterval
            perfQ.put({"name":"batchCompleted","batches":numIntervalTransactions,"latency":batchElapsedMs,"inserts":numIntervalTransactions,"exceptions":numIntervalExceptions})
            batchElapsedMs = 0.0
            numIntervalTransactions = 0
            numIntervalExceptions = 0
            perfQ.put({"name":"batchDetails","batches":numIntervalTransactions,"op1Ms":op1Ms,"op2Ms":op2Ms,"op3Ms":op3Ms,"op4Ms":op4Ms,"op5Ms":op5Ms,"op6Ms":op6Ms,"op7Ms":op7Ms,"op8Ms":op8Ms})
            op1Ms = 0.0
            op2Ms = 0.0
            op3Ms = 0.0
            op4Ms = 0.0
            op5Ms = 0.0
            op6Ms = 0.0
            op7Ms = 0.0
            op8Ms = 0.0
            
        if ((time.time() - startTime) >= runSeconds) and (runSeconds > 0):
            allDone = True

        if (numTotalTransactions >= numOperationsThisWorker) and (numOperationsThisWorker > 0):
            allDone = True
        
    client.close()
    
    perfQ.put({"name":"processCompleted","processNum":threadNum})


def main():
    warnings.filterwarnings("ignore","You appear to be connected to a DocumentDB cluster.")

    parser = argparse.ArgumentParser(description='Data Generator')

    parser.add_argument('--uri',required=True,type=str,help='URI (connection string)')
    parser.add_argument('--processes',required=True,type=int,help='Degree of concurrency')
    parser.add_argument('--database',required=True,type=str,help='Database')
    parser.add_argument('--collection',required=False,default='sbtest',type=str,help='Base name of collections')
    parser.add_argument('--run-seconds',required=False,type=int,default=0,help='Total number of seconds to run for')
    parser.add_argument('--num-operations',required=False,type=int,default=0,help='Total number of operations to run for')
    parser.add_argument('--num-collections',required=False,type=int,default=10,help='Number of collections')
    parser.add_argument('--num-documents-per-collection',required=False,type=int,default=5000000,help='Number of documents per collection')
    parser.add_argument('--load-batch-size',required=False,default=100,type=int,help='Number of documents to insert per batch during load')
    parser.add_argument('--rate-limit',required=False,type=int,default=9999999,help='Limit throughput (operations per second)')
    parser.add_argument('--pad-field-size',required=False,type=int,default=60,help='Size of pad field (bytes)')
    parser.add_argument('--compressible-field-size',required=False,type=int,default=0,help='Size of compressible field (bytes)')
    parser.add_argument('--ordered-batches',required=False,action='store_true',help='Use ordered bulk-writes')
    parser.add_argument('--compression',required=False,type=str,default='parmgroup',choices=['parmgroup','none','lz4','zstd'],help='Compression to use (or not)')
    parser.add_argument('--shard',required=False,action='store_true',help='Shard the collection')
    parser.add_argument('--file-name',required=False,type=str,default='benchmark',help='Starting name of the created CSV and log files')
    parser.add_argument('--change-stream',required=False,action='store_true',help='Enable change streams')
    parser.add_argument('--num-intervals-average',required=False,type=int,default=10,help='Number of intervals for averaging')
    parser.add_argument('--load',required=False,action='store_true',help='Load data')
    parser.add_argument('--run',required=False,action='store_true',help='Run the benchmark')
    parser.add_argument('--sysbench-range-size',required=False,type=int,default=100,help='Number of documents for sysbench range operations')
    parser.add_argument('--sysbench-point-queries',required=False,type=int,default=10,help='Number of single document find operations per sysbench transaction')
    parser.add_argument('--sysbench-simple-range-queries',required=False,type=int,default=1,help='Number of ranged find operations per sysbench transaction')
    parser.add_argument('--sysbench-sum-range-queries',required=False,type=int,default=1,help='Number of summed range aggregation operations per sysbench transaction')
    parser.add_argument('--sysbench-ordered-range-queries',required=False,type=int,default=1,help='Number of ordered range find operations per sysbench transaction')
    parser.add_argument('--sysbench-distinct-range-queries',required=False,type=int,default=1,help='Number of ranged distinct operations per sysbench transaction')
    parser.add_argument('--sysbench-indexed-updates',required=False,type=int,default=1,help='Number of single document indexed update operations per sysbench transaction')
    parser.add_argument('--sysbench-non-indexed-updates',required=False,type=int,default=1,help='Number of single document non-indexed update operations per sysbench transaction')
    parser.add_argument('--sysbench-deletes-then-inserts',required=False,type=int,default=1,help='Number of single document delete then insert operations per sysbench transaction')
    parser.add_argument('--index-for-queries',required=False,type=str,default='id',choices=['id','k'],help='Index to use for queries, id or k')
    parser.add_argument('--show-detailed-latencies',required=False,action='store_true',help='Show individual latencies for each step in the Sysbench transaction')

    args = parser.parse_args()

    if not args.load and not args.run:
        printLog("Must choose mode of --load or --run",appConfig)
        sys.exit(1)

    if args.load and args.run:
        printLog("Cannot choose both modes of --load and --run",appConfig)
        sys.exit(1)
    
    if args.shard and args.change_stream:
        printLog("Change streams are not currently supported on sharded collections",appConfig)
        sys.exit(1)

    appConfig = {}
    appConfig['uri'] = args.uri
    appConfig['numProcesses'] = int(args.processes)
    appConfig['databaseName'] = args.database
    appConfig['collectionName'] = args.collection
    appConfig['runSeconds'] = int(args.run_seconds)
    appConfig['numOperations'] = int(args.num_operations)
    appConfig['numDocumentsPerCollection'] = int(args.num_documents_per_collection)
    appConfig['numCollections'] = int(args.num_collections)
    appConfig['rateLimit'] = int(args.rate_limit)
    appConfig['loadBatchSize'] = int(args.load_batch_size)
    appConfig['orderedBatches'] = args.ordered_batches
    appConfig['compression'] = args.compression
    appConfig['shard'] = args.shard
    appConfig['logFileName'] = "{}.log".format(args.file_name)
    appConfig['csvFileName'] = "{}.csv".format(args.file_name)
    appConfig['changeStream'] = args.change_stream
    appConfig['numIntervalsAverage'] = int(args.num_intervals_average)
    appConfig['padFieldSize'] = int(args.pad_field_size)
    appConfig['compressibleFieldSize'] = int(args.compressible_field_size)
    appConfig['modeLoad'] = args.load
    appConfig['modeRun'] = args.run
    appConfig['sysbenchRangeSize'] = int(args.sysbench_range_size)
    appConfig['sysbenchPointQueries'] = int(args.sysbench_point_queries)
    appConfig['sysbenchSimpleRangeQueries'] = int(args.sysbench_simple_range_queries)
    appConfig['sysbenchSumRangeQueries'] = int(args.sysbench_sum_range_queries)
    appConfig['sysbenchOrderedRangeQueries'] = int(args.sysbench_ordered_range_queries)
    appConfig['sysbenchDistinctRangeQueries'] = int(args.sysbench_distinct_range_queries)
    appConfig['sysbenchIndexedUpdates'] = int(args.sysbench_indexed_updates)
    appConfig['sysbenchNonIndexedUpdates'] = int(args.sysbench_non_indexed_updates)
    appConfig['sysbenchDeletesThenInserts'] = int(args.sysbench_deletes_then_inserts)
    appConfig['indexForQueries'] = args.index_for_queries
    appConfig['showDetailedLatencies'] = args.show_detailed_latencies

    # parameterized but not user facing
    appConfig['cFieldSize'] = 120

    if (appConfig['runSeconds'] == 0 and appConfig['numOperations'] == 0 and appConfig['modeRun']):
        printLog("Must supply non-zero for one of --run-seconds or --num-operations when executing the benchmark",appConfig)
        sys.exit(1)

    if (appConfig['runSeconds'] > 0 and appConfig['numOperations'] > 0):
        printLog("Cannot supply non-zero for both --run-seconds and --num-operations",appConfig)
        sys.exit(1)

    if (appConfig['runSeconds'] > 0 and appConfig['modeLoad']):
        printLog("--run-seconds must be zero when loading data",appConfig)
        sys.exit(1)

    if (appConfig['numOperations'] > 0 and appConfig['modeLoad']):
        printLog("--num-operations must be zero when loading data",appConfig)
        sys.exit(1)

    if (appConfig['numProcesses'] > 0 and appConfig['modeLoad']):
        printLog("--num-processes must be zero when loading data, it is automatically set to --num-collections",appConfig)
        sys.exit(1)
    
    numExistingDocuments = 0

    if appConfig['modeLoad']:
        appConfig['numProcesses'] = appConfig['numCollections']
        numExistingDocuments = setup_load(appConfig)
    else:
        numExistingDocuments = setup_run(appConfig)
        appConfig['numDocumentsPerCollection'] = numExistingDocuments
    
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
    for loop in range(appConfig['numProcesses']):
        #time.sleep(1)
        if appConfig['modeLoad']:
            p = mp.Process(target=load_worker,args=(loop,q,appConfig))
            processList.append(p)
        else:
            p = mp.Process(target=run_worker,args=(loop,q,appConfig))
            processList.append(p)
        
    for process in processList:
        process.start()
        
    for process in processList:
        process.join()
        
    t.join()
    
    reportCollectionInfo(appConfig)
    reportDatabaseInfo(appConfig)

    cleanup(appConfig)
    
    printLog("Created {} and {} with results".format(appConfig['logFileName'],appConfig['csvFileName']),appConfig)


if __name__ == "__main__":
    main()
