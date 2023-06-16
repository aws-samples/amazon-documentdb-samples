import os
import pymongo
import random
import time

username = os.environ.get("docdbUser")
password = os.environ.get("docdbPass")
clusterendpoint = os.environ.get("docdbEndpoint")
client = pymongo.MongoClient(clusterendpoint, username=username, password=password, tls='true', tlsCAFile='rds-combined-ca-bundle.pem', retryWrites='false', appName='statesByCarMake-py')
db = client["pi"]
carMakers = db["customers"].find({"_id":"carMakers"})[0]

for x in range(1000):
    time.sleep(1)
    carMaker = random.choice(carMakers["carMakers"])

    pipeline = [
        {
            '$match': {
                'CarData.CarMaker': carMaker
            }
        },
        {
            '$group': {
                '_id': '$State',
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

    print("Top states for", carMaker, "owners")
    results = db["customers"].aggregate(pipeline)
    for result in results:
        print(result)

    client.close
