# Python Updater tool 
This sample applications compresses pre-existing documents in an existing collection after compression is turned on that existing collection.

Single threaded application - issues 5000 updated serially in a round, and sleeps for 60 seconds before starting next round.

Status of the updates are maintained in database **tracker_db** - for each collection there is a tracker collection named **<<collection>>__tracker_col**.

The application can be restarted if it crashes and it will pick up from last round based on data in **<<collection>>__tracker_col**.

The update statements use field **temp_field_for_compressor** , for triggering compression on existing records.

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
