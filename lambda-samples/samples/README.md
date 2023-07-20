# Lambda Functions samples

This repository contains AWS Lambda functions designed to interact with an Amazon DocumentDB cluster. 

## Functions

### 1. docdb-crud.py

**Description:**  
The `docdb-crud.py` Lambda function exemplify CRUD (Create, Read, Update, Delete) operations against data stored in the Amazon DocumentDB cluster. You need to create a secret in AWS Secrets Manager containing the credentials to Amazon DocumentDB.

**Runtime:**  
Python 3.x

**Dependencies:**
- pymongo: Required to establish connections and perform operations with the Amazon DocumentDB cluster. Add a layer that contains the Python module.

**Environment variables:**
- DOCDB_SECRET_NAME: The name of the secret in AWS Secrets Manager containing DocumentDB credentials.
- DOCDB_DATABASE: The name of DocumentDB database.
- DOCDB_COLLECTION: The name of the DocumentDB collection.


### 2. docdb-stopStart.py

**Description:**  
The `docdb-stopStart.py` Lambda function allows you to stop and start the Amazon DocumentDB cluster as needed for cost optimization and to manage resource utilization efficiently. The function stops clusters configured with the tag `AllowStop: true` and starts clusters configured with the tag `AllowStart: true`. [Create an Eventbridge rule](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-run-lambda-schedule.html#eb-schedule-create-rule) to schedule the execution of the Lambda function.

**Runtime:**  
Python 3.x

**Dependencies:**
- boto3: Required to interact with AWS services, including starting and stopping the DocumentDB cluster. This comes included in the Lambda environment, no need to add a layer.
- Lambda role requires the necessary permissions to stop/start an Amazon DocumentDB cluster. The policy attached with the role should contain:

```
{
  "Version": "2012-10-17",
  "Statement": [
      {
          "Sid": "VisualEditor0",
          "Effect": "Allow",
          "Action": [
              "rds:DescribeDBClusterParameters",
              "rds:StartDBCluster",
              "rds:StopDBCluster",
              "rds:DescribeDBEngineVersions",
              "rds:DescribeGlobalClusters",
              "rds:DescribePendingMaintenanceActions",
              "rds:DescribeDBLogFiles",
              "rds:StopDBInstance",
              "rds:StartDBInstance",
              "rds:DescribeReservedDBInstancesOfferings",
              "rds:DescribeReservedDBInstances",
              "rds:ListTagsForResource",
              "rds:DescribeValidDBInstanceModifications",
              "rds:DescribeDBInstances",
              "rds:DescribeSourceRegions",
              "rds:DescribeDBClusterEndpoints",
              "rds:DescribeDBClusters",
              "rds:DescribeDBClusterParameterGroups",
              "rds:DescribeOptionGroups"
          ],
          "Resource": "*"
      }
  ]
}
```

**Environment variables:**
- ACTION: value can be `stop` to stop clusters, or `start` to start clusters.

### 3. docdb-killLongOp.py

**Description:**  
The `docdb-killLongOp.py` Lambda function will identify and terminate long-running operations in the Amazon DocumentDB cluster, to optimize its performance and resource utilization. [Create an Eventbridge rule](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-run-lambda-schedule.html#eb-schedule-create-rule) to schedule how often the Lambda function should be triggered for.

**Runtime:**  
Python 3.x

**Dependencies:**
- pymongo: Required to establish connections and interact with the MongoDB cluster. Add a layer that contains the Python module.

**Environment variables:**
 - DOCDB_SECRET_NAME: The name of the secret in AWS Secrets Manager containing DocumentDB credentials.
 - THRESHOLD_SECONDS: The number of seconds the operation is running for to be considered long running and stopped
