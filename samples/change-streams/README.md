# A solution to replicate AWS DocumentDB change stream events to different targets

This solution allows to replicate AWS DocumentDB change streams events to ElasticSearch, Amazon Managed Stream for Kafka (or any other Apache Kafka distro), SNS, AWS Kinesis Streams, AWS SQS, and/or S3. S3 replication is done in micro-batches and the rest of the integration are near real-time.  

This solution is composed of:
- One Amazon EventBridge rule in charge of triggering an SNS topic
- One SNS topic which publishes the event to one or more lambda functions
- One or more lambda functions, one per AWS DocumentDB collection, in charge of replicating events to the different targets. Everytime the function is triggered it queries the DocumentDB change stream for a specific collection and publishes the events to the targets

The Lambda functions run within a VPC therefore it is necessary that they are placed in at least one private subnet that can reach internet using a NAT gateway or privatelinks for the services it needs to integrate with. An Amazon Root CA certificate is required to communicate with Amazon ElasticSearch; if the Lambda does not have Internet access, make sure you load the certificate to the tmp folder of python virtual environment and comment the line of code that invokes the method to get the certificate. 

Each lambda function uses 3 variables to control how many events replicates; customers are encourage to tune this variables according to the throughput of each collection. This variables are: 
- The lambda function timeout which is set to 90 seconds
- MAX_LOOP is a control variable to avoid that the lambda times out in an inconsistent state. This is set to 45. 
- STATE_SYNC_COUNT is a control varible that determines how many iteration should the lambda wait before syncing the resume token (resume token is used to track the events processed in the change stream). It is meant to reduce IO operations on AWS DocumentDB. This is set to 15.

To enable a target, you need to include a value for its environment varibles within the lambda and add permissions to the lambda role and/or network accordingly. 

# How to install
0. Enable change streams. Follow instructions given here: https://docs.aws.amazon.com/documentdb/latest/developerguide/change-streams.html
1. Deploy a Cloud9 environment and clone this repo
2. Execute `export S3_BUCKET=s3://[Bucket Name]` where [Bucket Name] is the bucket that will host the lambda code used to replicate change stream events. 
3. Execute `chmod 700 docdb-replicator/setup/startup.sh` and execute `docdb-replicator/setup/startup.sh`. This setup bash will:
    1. Upgrade OS and install jq 
    2. Upgrade pip3, awscli, and node
    3. Install AWS Cloud Development Kit (CDK) and creates a CDK project 
    4. Upgrade the CDK project
    5. Deploy replication code into S3 bucket
4. Create a new secret in AWS Secrets Manager for the DocumentDB cluster
5. Create two AWS SNS topics:
    1. One for alerting exceptions
    2. Triggering lambda functions
6. Create a AWS EventBridge rule and configure the SNS topic, that will trigger the lambda functions, as target. Also set the scheduler for it accordingly. 
7. Modify the docdb-replication-builder/config.ini file accordingly
8. Uncomment targets in the docdb-replication-builder/config.ini file
9. Execute `cd docdb-replication-builder/`
10. Execute `source .env/bin/activate`
11. Execute `cdk synth` to validate there are not errors
12. Execute `cdk deploy`. Accept the changes that will be deploy. You can change the name of the CloudFormation Stack, in docdb-replication-builder/app.py    

# Environment Varibles for targets
When you set up a target, make sure Lambda can reach it and the role associated to the lambda has proper permissions (e.g. s3:PutObject). 

### ElasticSearch
One index will be automatically created per database and collection. 
- ELASTICSEARCH_URI: The URI of the Elasticsearch domain where data should be streamed.

### Kinesis
All events in the different collections will go to this stream. If you want otherwise, you need to update the environment variable for each lambda. 
- KINESIS_STREAM : The Kinesis Stream name to publish DocumentDB events.

### SQS
All events in the different collections will go to this queue. If you want otherwise, you need to update the environment variable for each lambda. 
- SQS_QUERY_URL: The URL of the Amazon SQS queue to which a message is sent.

### Kafka
One topic will be automatically created per database and collection. Make sure auto.create.topics.enable is set to true for the cluster configuration.   
- MSK_BOOTSTRAP_SRV: The URIs of the MSK cluster to publish messages. 

### S3
One folder will be automatically created per database and collection, and for each of them, folders for year, month, and day will be used to allocate micro-batches. 
- BUCKET_NAME: The name of the bucket that will save streamed data. 
- BUCKET_PATH: The path of the bucket that will save streamed data.  

### SNS
All events in the different collections will go to this topic. If you want otherwise, you need to update the environment variable for each lambda. 
- SNS_TOPIC_ARN_EVENT: The topic to send docdb events.    

# Keep in mind
- For each DocumentDB cluster, just one collection will be used to keep resume tokens. 
- SNS does not support ordering. If ordering is a must, do not use it as target. 
- Make sure message size limits on targets will support your documents size. 