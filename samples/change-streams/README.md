# A sample solution to stream AWS DocumentDB events to different targets

This sample solution allows to stream AWS DocumentDB events to Amazon Elasticsearch Service, Amazon Managed Stream for Kafka (or any other Apache Kafka distro), AWS Kinesis Streams, AWS SQS, and S3. S3 streaming is done in micro-batches and the rest of the integration are near real-time.  

This sample solution is composed of:

## Lambda Function

The AWS Lambda function will retrieve DocumentDB credential information from AWS Secrets Manager, make a connection to the DocumentDB cluster, retrieve the token for where the Lambda last left off in reading the change stream, and use that token to resume consuming change stream events.

The Lambda will read N change events from the Change Stream and stream them to each target, and then save the change stream token into DocumentDB to use the next time the Lambda is invoked.

The Lambda function also retrieve a certificate from Amazon S3 to connect via TLS to DocumentDB. 

This sample solution deploys one Lambda function that can be set via environment variables to stream changes in one collection or an entire database. 

Streaming functions must be deployed in a private subnet to reach DocumentDB cluster. 

Each lambda function uses 3 variables to control how many events streaming; customers are encourage to tune this variables according to the throughput of each collection. This variables are: 
- The lambda function timeout which is set to 120 seconds
- MAX_LOOP is a control variable to avoid that the lambda times out in an inconsistent state. This is set to 45. 
- STATE_SYNC_COUNT is a control varible that determines how many iteration should the lambda wait before syncing the resume token (resume token is used to track the events processed in the change stream). It is meant to reduce IO operations on Amazon DocumentDB. This is set to 15.

For target, there must be environment varibles in the lambda and permissions for the lambda role and/or network accordingly. 

Change Stream resumability was built around the resume token used within the watch api in options resumeAfter or startAfter. If there are not events when this Lambda function runs for the first time, it uses a canary to established a resume token for further executions.  

## SNS and EventBridge Rule

The sample solution will poll for changes every 120 seconds. It uses Amazon EventBridge to trigger a message to Amazon SNS, which will in turn invoke the AWS Lambda functions which does the bulk of the work.

# How to install
1. Enable __[change streams](https://docs.aws.amazon.com/documentdb/latest/developerguide/change-streams.html)__
2. Deploy a the baseline environment. 
    1. Go to AWS CloudFormation in AWS console and select *Create stack*. 
    2. Check the *Upload a template file* option, select *Choose file *option and upload the __[change stream stack](https://raw.githubusercontent.com/aws-samples/amazon-documentdb-samples/master/samples/change-streams/setup/docdb_change_streams.yml)__ yaml file, and select *Next.*
    3. Give your stack a name, and input username, password, the identifier for your Amazon DocumentDB cluster, select *Next*. 
    4. SWS Cloud9 uses a Role and an Instance profile. If you have used Cloud9 before, those have been created automatically for you; therefore, select *true* in the options for *ExistingCloud9Role* and *ExistingCloud9InstanceProfile*. Otherwise, leave it as *false*. 
    5. Leave everything as default and select *Next*. Check the box to allow the stack create a role on behalf of you and select *Create stack*. The stack should complete provisioning in a few minutes. 
3. Setup the Cloud9 environment
    1. From your AWS Cloud9 environment, launch a new tab to open the Preferences tab
    2. Select *AWS SETTINGS *from the left navigation pane
    3. Turn off *AWS managed temporary credentials. *This enables us to simplify the developer experience later in the walkthrough
    4. Close the Preferences tab 
    5. In a terminal window, execute `rm -vf ${HOME}/.aws/credentials`
    6. Create an environment variable for the CloudFormation stack by executing: 
        ```
        export STACK=<Name of your CloudFormation stack> 
        echo "export STACK=${STACK}" >> ~/.bash_profile
        ```
    7. Configure AWS cli to use the current region as the default: `export AWS_REGION=$(curl -s 169.254.169.254/latest/dynamic/instance-identity/document | grep region | cut -d\" -f4)`
    8. Execute the code below to update the environment libraries, upload streaming code to S3, and copy output from previous CloudFormation.
        ```
        wget https://raw.githubusercontent.com/aws-samples/amazon-documentdb-samples/master/samples/change-streams/setup/startup.sh
        chmod 700 startup.sh
        ./startup.sh
        ```
7. Execute the commands below to create and deploy the AWS CloudFormation stack that will be populated with the required environment variables - Amazon DocumentDB URI, Amazon Elasticsearch service domain URI, watched database name, collection name, state database name, state collection name , networking configuration, SNS topics ARN, Lambda role ARN, and the Secrets Manager ARN.
    ```
    wget https://raw.githubusercontent.com/aws-samples/amazon-documentdb-samples/master/samples/change-streams/setup/lambda_function_config.sh
    chmod 700 lambda_function_config.sh
    ./lambda_function_config.sh
    ```
8. Streaming code is set. You can test it by running `python test/es-test.py``
9. You can verify it by executing the following commmands:
   `curl https://$(jq < cfn-output.json -r '.ElasticsearchDomainEndpoint')/_cat/indices?v`

Once deployed, streaming functions will be run with the frequency set in the scheduling components. 

# Environment Varibles for targets
When you set up a target, make sure Lambda can reach it and the role associated to the lambda has proper permissions (e.g. s3:PutObject). 

### Elasticsearch
One index will be automatically created per database or collection. 
- ELASTICSEARCH_URI: The URI of the Elasticsearch domain where data should be streamed.

If Amazon Elasticsearch is a target, streaming functions must be deployed in a private subnet that can reach Internet to get an Amazon certificate required to publish to Elasticsearch. Otherwise, streaming code has to be modified and the certificate must be included in the Lambda package.

### Kinesis
All events will go to this stream.  
- KINESIS_STREAM : The Kinesis Stream name to publish DocumentDB events.

### SQS
All events will go to this queue. 
- SQS_QUERY_URL: The URL of the Amazon SQS queue to which a message is sent.

### Kafka
One topic will be automatically created per database or collection. Make sure auto.create.topics.enable is set to true for the cluster configuration.   
- MSK_BOOTSTRAP_SRV: The URIs of the MSK cluster to publish messages. 

### S3
One folder will be automatically created per database or collection, and for each of them, folders for year, month, and day will be used to allocate micro-batches. 
- BUCKET_NAME: The name of the bucket that will save streamed data. 
- BUCKET_PATH: The path of the bucket that will save streamed data.    

# Keep in mind
- Make sure message size limits on targets will support your documents size. 

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

## Questions/feature requests?
Email questions to: documentdb-feature-request@amazon.com