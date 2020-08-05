# A sample solution to stream AWS DocumentDB events to different targets

This sample solution allows to stream AWS DocumentDB events to ElasticSearch, Amazon Managed Stream for Kafka (or any other Apache Kafka distro), AWS Kinesis Streams, AWS SQS, and/or S3. S3 streaming is done in micro-batches and the rest of the integration are near real-time.  

This sample solution is composed of:

## Lambda Function

The AWS Lambda function will retrieve DocumentDB credential information from AWS Secrets Manager, make a connection to the DocumentDB cluster, retrieve the token for where the Lambda last left off in reading the change stream, and use that token to resume consuming change stream events.

The Lambda will read N change events from the Change Stream and stream them to each target, and then save the change stream token into DocumentDB to use the next time the Lambda is invoked.

The Lambda function also retrieve a certificate from Amazon S3 to connect via TLS to DocumentDB. 

This sample solution deploys one Lambda function per DocumentDB collection. 

Streaming functions must be deployed in a private subnet to reach DocumentDB cluster. 

Each lambda function uses 3 variables to control how many events streaming; customers are encourage to tune this variables according to the throughput of each collection. This variables are: 
- The lambda function timeout which is set to 120 seconds
- MAX_LOOP is a control variable to avoid that the lambda times out in an inconsistent state. This is set to 45. 
- STATE_SYNC_COUNT is a control varible that determines how many iteration should the lambda wait before syncing the resume token (resume token is used to track the events processed in the change stream). It is meant to reduce IO operations on Amazon DocumentDB. This is set to 15.

For target, there must be environment varibles in the lambda and permissions for the lambda role and/or network accordingly. 

## SNS and EventBridge Rule

The sample solution will poll for changes every 120 seconds. It uses Amazon EventBridge to trigger a message to Amazon SNS, which will in turn invoke the AWS Lambda functions which does the bulk of the work.

# How to install
1. Enable change streams. Follow instructions given here: https://docs.aws.amazon.com/documentdb/latest/developerguide/change-streams.html
2. Deploy a Cloud9 environment. Follow instructions given here: https://aws.amazon.com/blogs/database/part-2-getting-started-with-amazon-documentdb-using-aws-cloud9/
3. Create an S3 Bucket. In Cloud9 environment, execute `export S3_BUCKET=s3://[Bucket Name]` where [Bucket Name] is the bucket that will host the lambda code used to stream events. 
4. Setup the Cloud9 environment
    1. Create an app directory `mkdir app` and two files `touch app/requirements.txt & touch app/lambda_funtion.py`
    2. Copy the contents of the files in the app folder in this repo into the newly created ones 
    3. Create a setup file `touch startup.sh`
    4. Copy the contents of the cdk/startup.sh file in this repo into the newly created one
    5. Execute `chmod 700 startup.sh`
    6. Execute `./startup.sh`
5. Create a new secret in AWS Secrets Manager for the DocumentDB cluster
6. Create two AWS SNS topics:
    1. One for alerting exceptions `aws sns create-topic --name [sns_alert]`
    2. Triggering lambda functions `aws sns create-topic --name [sns_trigger]`
7. Create a AWS EventBridge rule and configure the SNS topic, that will trigger the lambda functions, as target. Also set the scheduler for it accordingly. 
    1. Execute `aws events put-rule --name [rule name] --schedule-expression "rate(2 minutes)" --state DISABLED`. This rule is set to run every 2 minutes and it is disabled. 
    2. Execute `aws events put-targets --rule [rule name] —targets "Id"="1","Arn"="[sns_trigger ARN]"`
8. Create role for the Lambda. The lambda needs the following base permissions:
    * AWSLambdaVPCAccessExecutionRole: this managed policy allows the lambda to run within a VPC.  
    * sns:Publish: this action is required for the lambda to publish exceptions to the topic.
    * secretsmanager:GetSecretValue: this action is required for the lambda to use the cluster credentials.
    * s3:GetObject: this action is required for the Lambda to get the certificate for TLS access to DocumentDB. 

    Additionally, the streaming function needs the permissions required to publish events to each target. 
9. Within Cloud9, setup the solution variables
    1. Create a config file `touch change-streams-project/config.ini`
    2. Copy the contents of the cdk/config.ini in the newly created file. 
    3. Replace the contents of the change_streams_project_stack.py with the file in this repo in cdk/change_streams_project_stack.py
    4. In the change_streams_project_stack.py file uncomment the targets where events will be streamed
    5. Fill the config.ini file with the variables of your environment
10. Execute `cd change-streams-project/`
11. Execute `source .env/bin/activate`
12. Execute `cdk synth` to validate there are not errors
13. Execute `cdk deploy`. Accept the changes that will be deploy. You can change the name of the CloudFormation Stack, in docdb-replication-builder/app.py 
14. Enable the EventBridge rule when everything is set   

Once deployed, streaming functions will be run with the frequency set in the scheduling components. 

# Environment Varibles for targets
When you set up a target, make sure Lambda can reach it and the role associated to the lambda has proper permissions (e.g. s3:PutObject). 

### Elasticsearch
One index will be automatically created per database and collection. 
- ELASTICSEARCH_URI: The URI of the Elasticsearch domain where data should be streamed.

If Amazon Elasticsearch is a target, streaming functions must be deployed in a private subnet that can reach Internet to get an Amazon certificate required to publish to Elasticsearch. Otherwise, streaming code has to be modified and the certificate must be included in the Lambda package.

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