# A solution to replicate AWS DocumentDB change stream events to different targets

This solution allows to replicate AWS DocumentDB change streams events to ElasticSearch, Amazon Managed Stream for Kafka (or any other Apache Kafka distro), AWS Kinesis Streams, AWS SQS, and/or S3. S3 replication is done in micro-batches and the rest of the integration are near real-time.  

This solution is composed of:
- One Amazon EventBridge rule in charge of triggering an SNS topic
- One Amazon SNS topic which publishes the event to one or more lambda functions
- One or more lambda functions, one per Amazon DocumentDB collection, in charge of replicating events to the different targets. Everytime the function is triggered it queries the DocumentDB change stream for a specific collection and publishes the events to the targets

Replication functions must be deployed in a private subnet to reach DocumentDB cluster. 

If Amazon ElasticSearch is a target, replication functions must be deployed in a private subnet that can reach Internet to get an Amazon certificate required to publish to ElasticSearch. Otherwise, replication code has to be modified and the certificate must be included in the Lambda package.

Each lambda function uses 3 variables to control how many events replicates; customers are encourage to tune this variables according to the throughput of each collection. This variables are: 
- The lambda function timeout which is set to 120 seconds
- MAX_LOOP is a control variable to avoid that the lambda times out in an inconsistent state. This is set to 45. 
- STATE_SYNC_COUNT is a control varible that determines how many iteration should the lambda wait before syncing the resume token (resume token is used to track the events processed in the change stream). It is meant to reduce IO operations on Amazon DocumentDB. This is set to 15.

For target, there must be environment varibles in the lambda and permissions for the lambda role and/or network accordingly. 

# How to install
1. Enable change streams. Follow instructions given here: https://docs.aws.amazon.com/documentdb/latest/developerguide/change-streams.html
2. Deploy a Cloud9 environment
3. Execute `export S3_BUCKET=s3://[Bucket Name]` where [Bucket Name] is the bucket that will host the lambda code used to replicate change stream events. 
4. Setup the Cloud9 environment
    1. Create an app directory `mkdir app` and two files `touch app/requirements.txt & touch app/lambda_funtion.py`
    2. Copy the contents of the files in the app folder in this repo into the newly created ones 
    3. Create a setup file `touch startup.sh`
    4. Copy the contents of the cdk/startup.sh file in this repo into the newly created one
    5. Execute `chmod 700 docdb-replicator/setup/startup.sh`
    6. Execute `docdb-replicator/setup/startup.sh`
5. Create a new secret in AWS Secrets Manager for the DocumentDB cluster
6. Create two AWS SNS topics:
    1. One for alerting exceptions
    2. Triggering lambda functions
7. Create a AWS EventBridge rule and configure the SNS topic, that will trigger the lambda functions, as target. Also set the scheduler for it accordingly. 
8. Create role for the Lambda. The lambda needs the following base permissions:
    * AWSLambdaVPCAccessExecutionRole: this managed policy allows the lambda to run within a VPC.  
    * sns:Publish: this action is required for the lambda to publish exceptions to the topic.
    * secretsmanager:GetSecretValue: this action is required for the lambda to use the cluster credentials.

    Additionally, the replication function needs the permissions required to publish events to each target. 

9. Within Cloud9, setup the solution variables
    1. Create a config file `touch change-streams-project/config.ini`
    2. Copy the contents of the cdk/config.ini in the newly created file. 
    3. Replace the contents of the change_streams_project_stack.py with the file in this repo in cdk/change_streams_project_stack.py
    4. In the change_streams_project_stack.py file uncomment the targets where events will be replicated
    5. Fill the config.ini file with the variables of your environment
10. Execute `cd change-streams-project/`
11. Execute `source .env/bin/activate`
12. Execute `cdk synth` to validate there are not errors
13. Execute `cdk deploy`. Accept the changes that will be deploy. You can change the name of the CloudFormation Stack, in docdb-replication-builder/app.py    

Once deployed, replication functions will be run with the frequency set in the scheduling components. 

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

# Keep in mind
- For each DocumentDB cluster, just one collection will be used to keep resume tokens. 
- Make sure message size limits on targets will support your documents size. 

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

## Questions/feature requests?
Email questions to: documentdb-feature-request@amazon.com