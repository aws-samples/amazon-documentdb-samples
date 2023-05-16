"""
  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
  SPDX-License-Identifier: MIT-0
 
  Permission is hereby granted, free of charge, to any person obtaining a copy of this
  software and associated documentation files (the "Software"), to deal in the Software
  without restriction, including without limitation the rights to use, copy, modify,
  merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
  permit persons to whom the Software is furnished to do so.
 
  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
  INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
  PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
  HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
  OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import os
import pymongo
import random
import time

username = os.environ.get("docdbUser")
password = os.environ.get("docdbPass")
clusterendpoint = os.environ.get("docdbEndpoint")
client = pymongo.MongoClient(clusterendpoint, username=username, password=password, tls='true', tlsCAFile='rds-combined-ca-bundle.pem', retryWrites='false', appName='petsByState-py')
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
