import datetime
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

def printLog(thisMessage,appConfig):
    print("{}".format(thisMessage))
    with open(appConfig['logFileName'], 'a') as fp:
        fp.write("{}\n".format(thisMessage))

def cleanup(appConfig):
    databaseName = appConfig['databaseName']
    collectionName = appConfig['collectionName']
    # client = pymongo.MongoClient(appConfig['uri'])
    # db = client[databaseName]
    # adminDb = client['admin']
    # nameSpace = "{}.{}".format(databaseName,collectionName)

    # client.close()

def setup(appConfig):

    databaseName = appConfig['databaseName']
    collectionName = appConfig['collectionName']

    client = pymongo.MongoClient(appConfig['uri'])

    db = client[databaseName]
    adminDb = client['admin']
    col = db[collectionName]

    tracker_db=client['tracker_db']
    trackerCollectionName = collectionName+'_tracker_col'
    tracker_col=tracker_db[trackerCollectionName]
    
    # check if collection exists, check if entry 


    list_of_collections = tracker_db.list_collection_names()  # Return a list of collections in 'tracker_db'
    print("list_of_collections {}".format(list_of_collections))
    
    # Check if collection "posts" exists in db (test_db)
    if trackerCollectionName in list_of_collections :

        result = tracker_col.find({}).sort({ "_id" : -1}).limit(1)
        
        
        
        for lastEntry in result :
            numExistingDocuments = lastEntry["numExistingDocuments"]
            maxObjectIdToTouch = lastEntry["maxObjectIdToTouch"]
            lastScannedObjectId = lastEntry["lastScannedObjectId"]
            numDocumentsUpdated = lastEntry["numDocumentsUpdated"]
            print("Found existing record: {}".format(str(lastEntry))) 

    else :      
        # try:
        result = col.find({},{ "_id" :1}).sort({ "_id" :-1}).limit(1)
        for id in result :
            print("result {}".format(result))
            maxObjectIdToTouch = id["_id"]
        lastScannedObjectId = 0
        numDocumentsUpdated = 0
        
        thisIndexName = 'idx_collectionName_ts'
            
        printLog("Creating index {}".format(thisIndexName),appConfig)
            
        tracker_col.create_index([('ts', pymongo.ASCENDING)], name=thisIndexName, background=False, unique=False)
            
        numExistingDocuments = col.estimated_document_count()
            
            
        first_entry = {
            "collection_name": appConfig['collectionName'],
            "lastScannedObjectId" : lastScannedObjectId,
            "ts": datetime.datetime.now(tz=datetime.timezone.utc),
            "maxObjectIdToTouch" : maxObjectIdToTouch,
            "numExistingDocuments" : numExistingDocuments,
            "numDocumentsUpdated" : numDocumentsUpdated
            # scan fields in future, for now we use  _id
            }   
            
        tracker_col.insert_one(first_entry)

        printLog("Insert entry {}".format(first_entry),appConfig)
            
            
            
            
            
        # except Exception as e:
        #     printLog( " Exception during SETUP : {}".format(str(e)),appConfig)
           
    client.close()

    returnData = {}
    returnData["numExistingDocuments"] = numExistingDocuments
    returnData["maxObjectIdToTouch"] = maxObjectIdToTouch
    returnData["lastScannedObjectId"] = lastScannedObjectId
    returnData["numDocumentsUpdated"] = numDocumentsUpdated
    
    print(returnData)

    return returnData


def task_worker(threadNum,perfQ,appConfig):


    rateLimit = appConfig['rateLimit']
    maxObjectIdToTouch = appConfig['maxObjectIdToTouch']
    lastScannedObjectId = appConfig['lastScannedObjectId']
    #runSeconds = appConfig['runSeconds']
    numInsertProcesses = appConfig['numInsertProcesses']

    
    numExistingDocuments = appConfig["numExistingDocuments"]
    maxObjectIdToTouch = appConfig["maxObjectIdToTouch"]
    lastScannedObjectId = appConfig["lastScannedObjectId"]
    numDocumentsUpdated = appConfig["numDocumentsUpdated"]






    client = pymongo.MongoClient(appConfig['uri'])
    myDatabaseName = appConfig['databaseName']
    db = client[myDatabaseName]
    myCollectionName = appConfig['collectionName']
    col = db[myCollectionName]
    
    
    tracker_db=client['tracker_db']
    trackerCollectionName = myCollectionName+'_tracker_col'
    tracker_col=tracker_db[trackerCollectionName]
    
    
    allDone = False

    tempLastScannedObjectId = lastScannedObjectId
    
    print(appConfig)

    while not allDone:

        #start and go through all the docs using _id 
        
        if lastScannedObjectId != 0 :
       
            batch =  col.find({"_id" : { "$gt" : lastScannedObjectId   }},{ "_id" :1}).sort({"_id" :1}).limit(appConfig['rateLimit'])
        else :
            
            batch =  col.find({},{ "_id" :1}).sort({ "_id" :1}).limit(appConfig['rateLimit'])
            
            
        batch_count = 0
        
        print("--------------batch_count : {}".format(batch_count))
        
        for id in batch : 
            # print("------------------{}----------------".format(id["_id"].generation_time))
            # print("------------------{}----------------".format(maxObjectIdToTouch.generation_time))
            # print("------------------{}----------------".format(id["_id"]))
            # print("------------------{}----------------".format(maxObjectIdToTouch))
            
            
            if id["_id"]<maxObjectIdToTouch:
                
                # print("found id {} lesser than maxObjectIdToTouch {}.".format(str(id["_id"]),str(maxObjectIdToTouch)))
                col.update_one({ "_id" : id["_id"] } , { "$set": { "temp_field_for_compressor": 1 } } )
                tempLastScannedObjectId = id["_id"]
                batch_count = batch_count + 1
                
            else:
                
                allDone = True
                print("found id {} higher than maxObjectIdToTouch {}. all done .stopping)".format(str(id["_id"]),str(maxObjectIdToTouch)))
                break
            
        
        # if  batch_count == 0 :
        #     allDone = True
        #     break
        
        # print("--------------numDocumentsUpdated : {}".format(numDocumentsUpdated))
        # print("--------------batch_count : {}".format(batch_count))
        
        
        if  batch_count > 0 :
        
            numDocumentsUpdated = numDocumentsUpdated + batch_count
        
            # print("--------------numDocumentsUpdated : {}".format(numDocumentsUpdated))

            tracker_entry = {
                "collection_name": appConfig['collectionName'],
                "lastScannedObjectId" : tempLastScannedObjectId,
                "date": datetime.datetime.now(tz=datetime.timezone.utc),
                "maxObjectIdToTouch" : maxObjectIdToTouch,
                "numExistingDocuments" : numExistingDocuments,
                "numDocumentsUpdated" : numDocumentsUpdated
                # scan fields in future, for now we use  _id
                }   
            
            tracker_col.insert_one(tracker_entry)
            printLog( " Last updates applied : {}".format(str(tracker_entry)),appConfig)
            lastScannedObjectId = tempLastScannedObjectId
        
            printLog("sleeping for {} seconds".format(appConfig['waitPeriod']),appConfig)
            time.sleep(appConfig['waitPeriod'])
        

                
    client.close()
    


def main():
    parser = argparse.ArgumentParser(description='Data Generator')

    parser.add_argument('--uri',required=True,type=str,help='URI (connection string)')
    parser.add_argument('--database',required=True,type=str,help='Database')
    parser.add_argument('--collection',required=True,type=str,help='Collection')
    parser.add_argument('--file-name',required=False,type=str,default='compressor',help='Starting name of the created log files')
    #parser.add_argument('--batch-size',required=True,type=int,help='Number of documents to read')
    #parser.add_argument('--wait-period',required=False,type=int,default=9999999,help='Number of seconds to wait between each batch')
    # parser.add_argument('--processes',required=True,type=int,help='Degree of concurrency')

    

    args = parser.parse_args()
    
    appConfig = {}
    appConfig['uri'] = args.uri
    appConfig['numInsertProcesses'] = 1 #int(args.processes)
    appConfig['databaseName'] = args.database
    appConfig['collectionName'] = args.collection
    appConfig['rateLimit'] = 5000  #int(args.rate_limit)
    appConfig['waitPeriod'] = 60 #int(args.wait_period)
    appConfig['logFileName'] = "{}.log".format(args.file_name)

    

    setUpdata = setup(appConfig)
    
    appConfig['numExistingDocuments'] = setUpdata["numExistingDocuments"]  
    appConfig['maxObjectIdToTouch'] = setUpdata["maxObjectIdToTouch"]  
    appConfig['lastScannedObjectId'] = setUpdata["lastScannedObjectId"]     
    appConfig['numDocumentsUpdated'] = setUpdata["numDocumentsUpdated"]   

    
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


    processList = []
    for loop in range(appConfig['numInsertProcesses']):
        #time.sleep(1)
        p = mp.Process(target=task_worker,args=(loop,q,appConfig))
        processList.append(p)
        
    for process in processList:
        process.start()
        
    for process in processList:
        process.join()
        
    # t.join()
    

    cleanup(appConfig)
    
    printLog("Created {}  with results".format(appConfig['logFileName']),appConfig)


if __name__ == "__main__":
    main()
