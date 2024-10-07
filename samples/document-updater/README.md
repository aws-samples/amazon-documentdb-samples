# Python Updater tool 
This sample applications compresses pre-existing documents in a collections after compression is turned on in an existing collection.

## Requirements
Python 3.6 or later, pymongo

## Installation
Clone the repository and go to the application folder:
```
git clone https://github.com/aws-samples/amazon-documentdb-samples.git
cd amazon-documentdb-samples/samples/document-updater
```

## Usage/Examples

```
 python3 updater.py --uri "<<documentdb_uri>>"  --database <<database>>   --collection <<collection>>
```

The application has the following arguments:

```
Required parameters
  --uri URI                                      URI (connection string)
  --processes PROCESSES                          Degree of concurrency
  --database DATABASE                            Database
  --collection COLLECTION                        Collection

```
