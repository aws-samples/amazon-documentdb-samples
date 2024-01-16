# Python Insert Benchmark (bench02)
This sample applications performs an insert-only workload on Amazon DocumentDB instance-based clusters and elastic clusters with several configurable parameters.

## Requirements
Python 3.6 or later, pymongo

## Installation
Clone the repository and go to the application folder:
```
git clone https://github.com/aws-samples/amazon-documentdb-samples.git
cd amazon-documentdb-samples/samples/python-bench02
```

## Usage/Examples
The application has the following arguments:
```
Required parameters
  --uri URI                                      URI (connection string)
  --processes PROCESSES                          Degree of concurrency
  --database DATABASE                            Database
  --collection COLLECTION                        Collection
  --run-seconds RUN_SECONDS                      Total number of seconds to run for
  --batch-size BATCH_SIZE                        Number of documents to insert per batch

Optional parameters
  --rate-limit RATE_LIMIT                        Limit throughput (operations per second), default=9999999
  --text-size TEXT_SIZE                          Size of text field (bytes), default=1024
  --text-compressible TEXT_COMPRESSIBLE          Compressibility of text field (percentage), default=25
  --ordered-batches                              Use ordered bulk-writes, default=unordered batches
  --drop-collection                              Drop the collection (if it exists), default=do not drop
  --compress                                     Compress the collection, default=no
  --shard                                        Shard the collection, default=no
  --num-customers NUM_CUSTOMERS                  Number of customers, default=10000
  --num-products NUM_PRODUCTS                    Number of products, default=1000000
  --max-quantity MAX_QUANTITY                    Maximum quantity, default=100000
  --seconds-date-range SECONDS_DATE_RANGE        Number of seconds for range of orderDate field, default=90*87400
  --num-secondary-indexes {0,1,2,3}              Number of secondary indexes, default=3
  --file-name FILE_NAME                          Starting name of the created CSV and log files, default="bench02-output"
```

