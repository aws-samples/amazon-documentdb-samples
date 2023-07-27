# Detecting low cardinality indexes for DocumentDB Performance 

Amazon DocumentDB uses a B-tree data structure for its indexes. A B-tree index uses a hierarchical structure that stores data in its nodes in a sorted order. B-Trees are excellent data structure for fast retrievals when index cardinality is high. As a rule of thumb Amazon DocumentDB indexes should have less than 1% selectivity. This script accepts documentdb cluster endpoint as a parameter and generates a report across all the databases and collections for indexes lower than threshold ( Default 1% ) provided. 

### Supported Parameters 

### Requirements 
* Python 3.9+ installed 
* Pandas 
* Mongo Client 4.0+ 
* AWS Cli and Amazon DocumentDB 

### Supported Parameters 

| Parameter        | Details          | Default  | Supported Values |
| ------------- |:-------------:| -----:| -----: |
| -s, --connection_string      | Connection String of Amazon DocumentDB Instance |  | |
| -m, --max_collections     | Maximum number of collections to scan in a database     | 100   | |
| -t, --threshold | Index Cardinality threshold percentage. Indexes with less than this % will be reported | 1 | |
| -d, --databases | Command separated list of databases to check cardinality | All | |
| -c, --collections | Command separated list of collections to check cardinality | All | |
| -sample, --sample_count | Max documents to sample for each index. Increasing this limit may result in higher IOPS cost and extended execution time | 100000 | |

### How to run the script 
1. Download CA cert file
    ```
    wget https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
    ```
2. Install python dependencies 
    ```
    sudo pip3 install pymongo boto3
    ```
3. Install mongo client and mongoimport util. This command requires an update if running on non-linux environments
    ```
    sudo yum install mongodb-org-tools
    echo -e "[mongodb-org-4.0] \nname=MongoDB Repository\nbaseurl=https://repo.mongodb.org/yum/amazon/2013.03/mongodb-org/4.0/x86_64/\ngpgcheck=1 \nenabled=1 \ngpgkey=https://www.mongodb.org/static/pgp/server-4.0.asc" | sudo tee /etc/yum.repos.d/mongodb-org-4.0.rep
    ```
3. Create test database, collection and indexes ( Skip this step if you are testing with your own database )
    ```
    mongo --ssl --host [DOCDB-CLUSTER-ENDPOINT]:27017 --sslCAFile global-bundle.pem --username [USERNAME] --password [PASSWORD]
    ```
    Replace [DOCDB-CLUSTER-ENDPOINT], [USERNAME] and [PASSWORD] to match your DocumentDB database. 

    then on mongo shell run following commands:
    ```
    use sampledatabase

    db.samplecollection.createIndex( { "Province_State": 1 } )
	db.samplecollection.createIndex( { "Combined_Key": 1 } )
	db.samplecollection.createIndex( { "Case_Type": 1 } )
	db.samplecollection.createIndex( { "Country_Region": 1 } )
	db.samplecollection.createIndex( { "Lat": 1, "Long": -1 } )
    ```
    Verify the indexes has been created using command:
    
    ```
    db.samplecollection.getIndexes()    
    ```
    
4. Exit mongo command prompt and load sample Data ( Skip this step if you are testing with your own database )
    ```
    wget https://raw.githubusercontent.com/aws-samples/amazon-documentdb-samples/master/datasets/cases.json

    mongoimport --ssl \
    --host="[DOCDB-CLUSTER-ENDPOINT]:27017" \
    --collection=samplecollection \
    --db=sampledatabase \
    --file=cases.json \
    --numInsertionWorkers 4 \
    --username=[USERNAME] \
    --password=[PASSWORD] \
    --sslCAFile global-bundle.pem

    ```
    Replace [DOCDB-CLUSTER-ENDPOINT], [USERNAME] and [PASSWORD] to match your DocumentDB database. 
5. Clone this repository locally 
    ```
    git clone https://github.com/aws-samples/amazon-documentdb-samples.git
    cd amazon-documentdb-samples/blogs/index-cardinality-detection
    pip install -r requirements.txt
    ```
5. Run  cardinality detection using the following code and review the results. 
    ```
    python3 detect-cardinality.py --connection_string "[DOCDB-CONNECTING-STRING]"
    ```
    * Update [DOCDB-CONNECTING-STRING] with the connection string format available in DocumentDB AWS Console


    This will produce the results similar to this:
    ```
    Starting Cardinality Check. Script may take few mins to finish.
    Finding indexes where Cardinality/Distinct Values are less than ( 1% )...


    ------------------------------------------
    Total Databases Found: 4
    Total collections Found across 4 database(s): 5
    Total indexes found : 5
    ------------------------------------------

    ------------------------------------------
    ######Found 3 indexes that may have low cardinality values.
    Top index(es) with lowest cardinality : ['Case_Type : 0.0006%', 'Province_State : 0.0403%', 'Country_Region : 0.0554%']
    ------------------------------------------
    Detailed report is generated and saved at `cardinality_output_2023-07-11T18:33:17.845754.csv`   
    ```

    Above output shows that 3 out of 5 indexes in the supplied DocumentDB clusters are of low cardinality. 
    
### How do you fix low cardinality indexes
1. Check if indexes are not utilized anymore. If so then go ahead and delete it. More details are available [Here](https://docs.aws.amazon.com/documentdb/latest/developerguide/user_diagnostics.html#user_diagnostics-identify_unused_indexes)
1. Convert low cardinality indexes into compound indexes if possible. This requires accessing your query patterns where more than 1 index is utilized in a query then it make sense to build a compound index instead. 
