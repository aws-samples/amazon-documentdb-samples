import os
import pymongo
import random
import time

username = os.environ.get("docdbUser")
password = os.environ.get("docdbPass")
clusterendpoint = os.environ.get("docdbEndpoint")
client = pymongo.MongoClient(clusterendpoint, username=username, password=password, tls='true', tlsCAFile='rds-combined-ca-bundle.pem', retryWrites='false', appName="carMakesByPet-py")
db = client["pi"]
pets = db["customers"].find({"_id":"pets"})[0]

for x in range(1000):
    time.sleep(.5)
    pet = random.choice(pets["pets"])

    pipeline = [
        {
            '$match': {
                'PetData.Pet': pet
            }
        },
        {
            '$group': {
                '_id': '$CarData.CarMaker',
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

    print("Top car makes for", pet, "owners")
    results = db["customers"].aggregate(pipeline)
    for result in results:
        print(result)

client.close
