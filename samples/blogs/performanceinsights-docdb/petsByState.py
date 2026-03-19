import os
import pymongo
import random
import time

username = os.environ.get("docdbUser")
password = os.environ.get("docdbPass")
clusterendpoint = os.environ.get("docdbEndpoint")
client = pymongo.MongoClient(clusterendpoint, username=username, password=password, tls='true', tlsCAFile='global-bundle.pem', retryWrites='false', appName='petsByState-py')
db = client["pi"]
states = db["customers"].find({"_id":"states"})[0]

for x in range(1000):
    time.sleep(.75)
    state = random.choice(states["states"])

    pipeline = [
        {
            '$match': {
                'State': state
            }
        },
        {
            '$group': {
                '_id': '$PetData.Pet',
                'count': {
                    '$sum': 1
                }
            }
        },
        {
            '$sort': {
                'count': -1
            }
        },
        {
            '$limit': 3
        }
    ]

    print("Top pets for customers in", state)
    results = db["customers"].aggregate(pipeline)
    for result in results:
        print(result)

    client.close
