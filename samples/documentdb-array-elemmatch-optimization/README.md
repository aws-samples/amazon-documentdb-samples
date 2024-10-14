# Introduction and Use Case

In  [Amazon DocumentDB](https://aws.amazon.com/documentdb/) ,for fields that have an array value, a multi-key in for fields that have an array value, a multi-key index allows you to create an index key for each element in the array. The array can be scalar (strings or numbers) and nested documents. When using multiple **$elemMatch** along with **$and** operator on indexed arrays containing nested objects as elements , Amazon DocumentDB query optimizer can utilize multikey indexes more efficiently when we arrange the query conditions on multikey index columns in increasing order of number of documents they match. This enables the narrowing down of the search scope of the first pass of the query execution to a fewer number of documents, leading to faster execution times.

You can elevate performance for workloads that query arrays by tailoring queries to the cardinality of your data. This project aims to facilitate the replication of test setups for Amazon DocumentDB, demonstrating performance enhancements through optimal rewriting of array queries. With insights into your dataset, crafting array queries tailored to DocumentDB's cloud native engine can significantly optimize execution.

### Sample dataset

The data used for this test was 1 million JSON documents each containing an array field called *metdata* .
The array field *metadata* contains two documents of the following structure


```bash
{
	"key" : "<<string>>"
	"value" : "<<string>>"
}
```

The value for the field "key", can be one of the following

* "cycle_number" 
* "registered" 

The following table illustrates their possible value in each nested document

| Key | Value |
| -------- | ------- 
| "cycle_number" | unique value text
| "registered"   | "YES" and "NO" in approximately 75:25 ratio

The following an example of what a document would look like once loaded to DocumentDB

```bash
db.index_optimization_coll.findOne()
{
  _id: ObjectId('6669c18996ed7881a1104351'),
  metadata: [
    {
      value: 'seven quintillion six hundred and sixty three quadrillion five hundred and fifty nine trillion seven hundred and seventy five billion four million five hundred and twenty thousand one hundred and seventy',
      key: 'cycle_number'
    },
    { value: 'NO', key: 'registered' }
  ]
}
```

## Deploy Infrastructure

### Run tests on your existing infrastructure

__Prerequisites__

- DocumentDB cluster with at least one db.r6g.large instance. You can use an existing DocumentDB cluster or create a new one.  This post assumes the default value for port (27017) and TLS (enabled) settings.
- [Amazon Cloud9](https://aws.amazon.com/pm/cloud9/) or [Amazon EC2 Instance](https://aws.amazon.com/pm/ec2/) (Amazon Linux 2023) that you can install test scripts and generate database connections.  You can use an existing Cloud9 or Amazon EC2 instance or create a new one.  For this test, we have used a Cloud9 m5.large instance type with Amazon Linux 2023.
- A security group that enables you to connect to your Amazon DocumentDB cluster from your Cloud9 environment. You can use an existing security group or [create a new one](https://docs.aws.amazon.com/documentdb/latest/developerguide/get-started-guide.html#cloud9-security).
- [mongoshell](https://www.mongodb.com/docs/mongodb-shell/install/) utility

## Clone code from Git repository to your Cloud9 environment

1. Log into the Cloud9 instance  

2. Clone this repository

```bash
git clone https://github.com/aws-samples/amazon-documentdb-samples.git
cd amazon-documentdb-samples/samples/documentdb-array-elemmatch-optimisation/
```
## Setup Test Environment


1. Configure enviroment details by running the `set_env_docdb.sh` file


Modify the *set_env_docdb.sh* file with your host and password
```

export DOCDB_HOST="<<docdb_cluster_endpoint>>"
export DOCDB_DB="index_optimization_db"
export DOCDB_COL="index_optimization_coll"
export DOCDB_USER="<<docdb_user>>"
export DOCDB_PASS="<<docdb_password>>"
export DOCDB_PORT=27017
```

Set your environment by running the *set_env_docdb.sh* file
```bash
. set_env_docdb.sh
```

2. Install Java 17 –

```bash
sudo yum install java-17-amazon-corretto-devel
```

3. To connect to the TLS enabled DocumentDB cluster (default setting), use the following steps to create the java certificate file .Create a java trust-store using these  [_instructions_](https://docs.aws.amazon.com/documentdb/latest/developerguide/connect_programmatically.html)
    1. mkdir /tmp/certs
    2. copy the script, listed below, fill in the place holders , into a file named create-truststore.sh.

        ```
        mydir=/tmp/certs
        truststore=${mydir}/rds-truststore.jks
        storepassword=<<password>>
        curl -sS "https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem" > ${mydir}/global-bundle.pem
        awk 'split_after == 1 {n++;split_after=0} /-----END CERTIFICATE-----/ {split_after=1}{print > "rds-ca-" n ".pem"}' < ${mydir}/global-bundle.pem
        for CERT in rds-ca-*; do
        alias=$(openssl x509 -noout -text -in $CERT | perl -ne 'next unless /Subject:/; s/.*(CN=|CN = )//; print')
        echo "Importing $alias"
        keytool -import -file ${CERT} -alias "${alias}" -storepass ${storepassword} -keystore ${truststore} -noprompt
        rm $CERT
        done
        rm ${mydir}/global-bundle.pem
        echo "Trust store content is: "
        keytool -list -v -keystore "$truststore" -storepass ${storepassword} | grep Alias | cut -d " " -f3- | while read alias
        do
        expiry=`keytool -list -v -keystore "$truststore" -storepass ${storepassword} -alias "${alias}" | grep Valid | perl -ne 'if(/until: (.*?)\n/) { print "$1\n"; }'`
        echo " Certificate ${alias} expires in '$expiry'"
        done
        ```

	3. chmod 777 *create-truststore.sh*
	4. ./create-truststore.sh
	
6. Download the nb5 jar from Github
    1. wget [https://github.com/nosqlbench/nosqlbench/releases/download/5.17.3-release/nb5.jar](https://github.com/nosqlbench/nosqlbench/releases/download/5.17.3-release/nb5.jar)
    2. chmod 777 nb5.jar

## Run tests


1. Connect to DocumentDB 


```bash
mongosh --ssl --host $DOCDB_HOST:$DOCDB_PORT --retryWrites=False --sslCAFile global-bundle.pem --username $DOCDB_USER --password $DOCDB_PASS
```


2. Create index on nested documents fields in the array *metadata*


```mongosh
use index_optimization_db
db.index_optimization_coll.createIndex({"metadata.key":1,"metadata.value":1})
```

3. Load data with nosqlbench, replace value for placeholder for truststore password

```bash
java -Djavax.net.ssl.trustStore=/tmp/certs/rds-truststore.jks -Djavax.net.ssl.trustStorePassword=<<password>> -jar nb5.jar run driver=mongodb yaml=load_sample_data_array_optimization.yaml connection="mongodb://$DOCDB_USER:$DOCDB_PASS@$DOCDB_HOST:$DOCDB_PORT/?tls=true&tlsCAFile=global-bundle.pem&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false" tags=block:"rampup.*" database=$DOCDB_DB cycles=1M threads=auto errors=timer,warn -v --report-csv-to ~/environment/tmp/charter_csv/$(date +%Y%m%d%H%M%S) --progress console:30s
```

Wait for the process to complete.Verify with mongoshell using the following command

```bash
db.index_optimization_coll.stats()
{
  ns: 'index_optimization_db.index_optimization_coll',
  count: 1000000,
  size: 380000000,
  avgObjSize: 380.01765,
  storageSize: 429768704,
  compression: { enable: false },
  capped: false,
  nindexes: 2,
  totalIndexSize: 537165824,
  indexSizes: { _id_: 51838976, 'metadata.key_1_metadata.value_1': 485326848 },
  collScans: 6,
  idxScans: 0,
  opCounter: { numDocsIns: 996811, numDocsUpd: 0, numDocsDel: 0 },
  cacheStats: {
    collBlksHit: 2487006,
    collBlksRead: 1298,
    collHitRatio: 99.9479,
    idxBlksHit: 12418671,
    idxBlksRead: 65371,
    idxHitRatio: 99.4764
  },
  lastReset: '2024-06-12 15:39:47.794722+00',
  ok: 1,
  operationTime: Timestamp({ t: 1718207110, i: 1 })
}
```

4. Find a sample value for cycle_number for query execution.

Execute the following query to get a valid *cycle_number* value for *key* equals *register* and *value* is *YES*. **We will be using this value in all subsequent tests.**

```
db.index_optimization_coll.findOne( {"metadata": { "$elemMatch": { "key": "registered", "value": "YES" } }});
{
  _id: ObjectId('6669c18996ed7881a03d6741'),
  metadata: [
    {
      value: 'eight quintillion nine hundred and forty seven quadrillion four hundred and sixty three trillion five hundred and nineteen billion nine hundred and twenty seven million one hundred and eighteen thousand three hundred and eighty six',
      key: 'cycle_number'
    },
    { value: 'YES', key: 'registered' }
  ]
}
```
**Note** the value **"eight quintillion nine hundred and forty seven quadrillion four hundred and sixty three trillion five hundred and nineteen billion nine hundred and twenty seven million one hundred and eighteen thousand three hundred and eighty six"** might not exist in your dataset, substitute this value with whatever you get from the output  of your query.

4. Run query 

We run a query with two $elemMatch filters on the metadata array field, combined with an $and operator in following order 

* key is "registered" and value is  "YES" which should result in ~750K documents match.
* key is "cycle_number" and value is  "seven quintillion four hundred and ninety one quadrillion six hundred and eighty trillion two hundred and thirty five billion seven hundred and fourteen million five hundred and thirty nine thousand eight hundred and eighty five" which should result in 1 document match.

```mongosh
db.index_optimization_coll.explain("executionStats").aggregate([ 
	{ "$match": 
		{ 
			"$and" :[
						{ "metadata": { "$elemMatch": { "key": "registered", "value": "YES" } } },
						{ "metadata": { "$elemMatch": { "key": "cycle_number", "value": "eight quintillion nine hundred and forty seven quadrillion four hundred and sixty three trillion five hundred and nineteen billion nine hundred and twenty seven million one hundred and eighteen thousand three hundred and eighty six" } } }
					]
		}
	}
])
```

The output in the console should look similar to the following 


```
{
  queryPlanner: {
    plannerVersion: 1,
    namespace: 'index_optimization_db.index_optimization_coll',
    winningPlan: {
      stage: 'FETCH',
      inputStage: { stage: 'IXSCAN', indexName: 'metadata.key_1_metadata.value_1' }
    }
  },
  executionStats: {
    executionSuccess: true,
    executionTimeMillis: '8238.725',
    planningTimeMillis: '0.228',
    executionStages: {
      stage: 'FETCH',
      nReturned: '1',
      executionTimeMillisEstimate: '8238.131',
      inputStages: [
        {
          stage: 'IXSCAN',
          nReturned: '751069',
          executionTimeMillisEstimate: '346.082',
          indexName: 'metadata.key_1_metadata.value_1'
        },
        { nReturned: '1', executionTimeMillisEstimate: '0.005' },
        { nReturned: '0', executionTimeMillisEstimate: '0.005' }
      ]
    }
  },
  serverInfo: { host: 'docdb-2024-06-05-16-29-08', port: 27017, version: '5.0.0' },
  ok: 1,
  operationTime: Timestamp({ t: 1718207761, i: 1 })
}
```

Note that even though the query returned 1 document, it had to FETCH and apply "cycle_number" filter for all the ~750K documents that the IXSCAN stage matched. This is not an efficient query execution path - total execution time is more than 3 seconds.

- Query begins by using the index we created, doing an index lookup on all documents that match the condition : key is "registered" and value is "YES"
- The selectivity of documents matching this filter is  75% of the  data.
- As a result, the index scan selects approximately 75%, equivalent to around ~750K documents, and doing subsequent filters on the documents it looked up

5. Run modified query

We rerun the query with two $elemMatch filters on the metadata array field, combined with an $and operator in following order 

* key is "cycle_number" and value is  "seven quintillion four hundred and ninety one quadrillion six hundred and eighty trillion two hundred and thirty five billion seven hundred and fourteen million five hundred and thirty nine thousand eight hundred and eighty five" which should result in 1 document match.
* key is "registered" and value is  "YES" which should result in about ~750K documents match.

```mongosh
db.index_optimization_coll.explain("executionStats").aggregate([ 
	{ "$match": 
		{ 
			"$and" :[
						{ "metadata": { "$elemMatch": { "key": "cycle_number", "value": "eight quintillion nine hundred and forty seven quadrillion four hundred and sixty three trillion five hundred and nineteen billion nine hundred and twenty seven million one hundred and eighteen thousand three hundred and eighty six" } } },
						{ "metadata": { "$elemMatch": { "key": "registered", "value": "YES" } } } 
					]
		}
	}
])

```

The output in the console should look similar to the following 

```bash
{
  queryPlanner: {
    plannerVersion: 1,
    namespace: 'index_optimization_db.index_optimization_coll',
    winningPlan: {
      stage: 'FETCH',
      inputStage: { stage: 'IXSCAN', indexName: 'metadata.key_1_metadata.value_1' }
    }
  },
  executionStats: {
    executionSuccess: true,
    executionTimeMillis: '0.599',
    planningTimeMillis: '0.466',
    executionStages: {
      stage: 'FETCH',
      nReturned: '1',
      executionTimeMillisEstimate: '0.061',
      inputStages: [
        {
          stage: 'IXSCAN',
          nReturned: '1',
          executionTimeMillisEstimate: '0.024',
          indexName: 'metadata.key_1_metadata.value_1'
        },
        { nReturned: '1', executionTimeMillisEstimate: '0.018' },
        { nReturned: '1', executionTimeMillisEstimate: '0.010' }
      ]
    }
  },
  serverInfo: { host: 'docdb-2024-06-05-16-29-08', port: 27017, version: '5.0.0' },
  ok: 1,
  operationTime: Timestamp({ t: 1718207815, i: 1 })
}
```

Note that the overall execution time is in sub milliseconds. The FETCH stage had to apply  filter only on the one document that the IXSCAN stage matched. 

- Query execution begins by using the index we created,doing an index lookup on all documents that match the condition  : key is "cycle_number" and value is  "seven quintillion four hundred and ninety one quadrillion six hundred and eighty trillion two hundred and thirty five billion seven hundred and fourteen million five hundred and thirty nine thousand eight hundred and eighty five" .
- The selectivity of documents matching this filter is  just 1 document.
- As a result, the index scan selects just 1 document and subsequent execution steps are very fast.

## Conclusion

When using multiple $elemMatch along with $and operator, on indexed arrays containing nested objects, in DocumentDB, you get better performance and efficient execution when you structure your query with a good understanding of the cardinality of your data. As a best practice, order your $elemMatch filters such that elements that have the most unique data, are first in order in your query.

### Credits

[Matt Shelton](https://www.linkedin.com/in/mashelton/)

[Sourav Biswas](https://www.linkedin.com/in/biswassourav/)
