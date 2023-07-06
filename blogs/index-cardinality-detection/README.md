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
| -n, --name      | Neptune instance name |  | |
| -r, --region     | Region name for instance      |    | |
| -p, --period | Number of days datapoints collected from cloudwatch      |    14 | |
| -s, --stats | Type of stats to collect and compare against      | Maximum |  Maximum, P90, Avg |


### How to run the script 
1. Download CA cert file
2. Install python dependencies 
3. Install mongo client 
3. Create test database, collection and indexes ( Skip this step if you are testing with your own database )
4. Load Sample Data ( Skip this step if you are testing with your own database )
5. Run  cardinality detection using the following code and review the results. 


### How do you fix low cardinality indexes
1. Check if indexes are not utilized anymore. If so then go ahead and delete it. 
1. Convert existing indexes into compound indexes