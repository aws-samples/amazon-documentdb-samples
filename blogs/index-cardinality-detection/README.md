# Detecting low cardinality indexes for DocumentDB Performance 

Amazon DocumentDB uses a B-tree data structure for its indexes. A B-tree index uses a hierarchical structure that stores data in its nodes in a sorted order. B-Trees are excellent data structure for fast retrievals when index cardinality is high. As a rule of thumb Amazon DocumnetDB indexes should have less than 1% selectivity. This script accepts documentdb cluster endpoint as a parameter and generates a report across all the databases and collections for indexes lower than threshold ( Default 1% ) provided. 

### Supported Parameters 

### Requirements 
* Python 3.9+ installed 
* Boto3 
* Mongo Client 4.0+ 
* AWS Cli and Amazon DocumnetDB 

### Supported Parameters 

| Parameter        | Details          | Default  | Supported Values |
| ------------- |:-------------:| -----:| -----: |
| -c, --connection_string      | Connection String of Amazon DocumentDB Instance |  | |
| -m, --max_collections     | Maximum number of collections to scan in a database     | 100   | |
| -t, --threshold | Index Cardinality threshold percentage | 1 | |

### How to run the script 
1. Download CA cert file
    ```
    wget https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
    ```
2. Install python dependencies 
    ```
    sudo pip3 install pymongo boto3
    ```
3. Install mongo client 
    ```
    echo -e "[mongodb-org-4.0] \nname=MongoDB Repository\nbaseurl=https://repo.mongodb.org/yum/amazon/2013.03/mongodb-org/4.0/x86_64/\ngpgcheck=1 \nenabled=1 \ngpgkey=https://www.mongodb.org/static/pgp/server-4.0.asc" | sudo tee /etc/yum.repos.d/mongodb-org-4.0.rep
    ```
3. Create test database, collection and indexes ( Skip this step if you are testing with your own database )
    ```
    mongo --ssl --host [DOCDB-CLUSTER-ENDPOINT]:27017 --sslCAFile global-bundle.pem --username [USERNAME] --password [PASSWORD]

    ```
    Replace [DOCDB-CLUSTER-ENDPOINT], [USERNAME] and [PASSWORD] to match your DocumentDB database. 
4. Load Sample Data ( Skip this step if you are testing with your own database )
    ```
    wget https://raw.githubusercontent.com/aws-samples/amazon-documentdb-samples/master/datasets/cases.json

    mongoimport --ssl \
    --host="[DOCDB-CLUSTER-ENDPOINT]:27017" \
    --collection=sample-collection \
    --db=sample-database \
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
    ```
5. Run  cardinality detection using the following code and review the results. 
    ```
    python3 detect-cardinality.py --connection_string [DOCDB-CONNECTING-STRING]
    ```
    * Update [DOCDB-CONNECTING-STRING] with the format mongodb://[username:password@][DOCDB-CLUSTER-ENDPOINT]:27017


    This will produce the results similar to this:
    ```
    cardinality= 0.00014862916913015872 hence threshold breached =  Y
    cardinality= 0.0038479654743183004 hence threshold breached =  Y
    cardinality= 2.1857230754435107e-06 hence threshold breached =  Y
    cardinality= 0.00020436510755396823 hence threshold breached =  Y
    cardinality= 0.0037222863974802982 hence threshold breached =  Y
    cardinality= 0.0037233792590180203 hence threshold breached =  Y

    ----------------------------------------
    Total Databases Found: 2
    Total Collections across Databases Found: 3
    Total Indexes across Collections: 6
    ----------------------------------------
    Found 6 index(es) with cardinality <= 1.0% across 3 collection(s) and 2 database(s).
    Check the CSV file generated at results-2023-07-07T18:42:33.995726.csv for details.    
    ```
### How do you fix low cardinality indexes
1. Check if indexes are not utilized anymore. If so then go ahead and delete it. More details are available [Here](https://docs.aws.amazon.com/documentdb/latest/developerguide/user_diagnostics.html#user_diagnostics-identify_unused_indexes)
1. Convert low cardinality indexes into compound indexes if possible. This requires accessing your query patterns where more than 1 index is utilized in a query then it make sense to build a compound index instead. 
