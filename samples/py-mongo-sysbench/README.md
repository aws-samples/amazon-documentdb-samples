# py-mongo-sysbench
Python implementation of [Sysbench](https://github.com/akopytov/sysbench) for MongoDB compatible databases.

Sysbench is a mixed workload containing point queries, range queries/aggregations, insert, update, and delete operations.

A single Sysbench transaction (by default) consists of the following operations -
* All range queries are 100 documents
* 10 point queries
* 1 unordered range query
* 1 ordered range query (unindexed)
* 1 aggregation (sum)
* 1 distinct range operation
* 1 indexed update
* 1 unindexed update
* 1 delete/re-insert (same _id for both)

## Requirements
Python 3.6 or later, pymongo

## Installation
Clone the repository and go to the application folder:
```
git clone https://github.com/aws-samples/amazon-documentdb-samples.git
cd amazon-documentdb-samples/samples/py-mongo-sysbench
```

## Usage/Examples
The Sysbench supports the following parameters.
```
Required parameters
  --uri URI                                      URI (connection string)
  --processes PROCESSES                          Degree of concurrency for run phase, load phase creates 1 loader per collection
  --database DATABASE                            Database
  --collection COLLECTION                        Collection base name
  --load-batch-size BATCH_SIZE                   Number of documents to insert per batch in load phase

  Must supply exactly 1 of the following
    --load                                       Load data
    --run                                        Run the benchmark

  In --load mode, supply the number of documents per collection 
    --num-documents-per-collection NUM_DOCS

  In --run mode, supply the number of seconds or the number of operations (Sysbench transactions)
    --run-seconds RUN_SECONDS
    --num-operations NUM_OPERATIONS

Optional parameters
  --rate-limit RATE_LIMIT                        Limit throughput (operations per second), default=9999999
  --pad-field-size PAD_FIELD_SIZE                Size of text field (bytes), default=60
  --ordered-batches                              Use ordered bulk-writes, default=unordered batches
  --compress                                     Compress the collection, default=no
  --shard                                        Shard the collection, default=no
  --num-intervals-average NUM_INTERVALS_AVERAGE  Number of intervals for averaging recent tps and latency, default=10
```

