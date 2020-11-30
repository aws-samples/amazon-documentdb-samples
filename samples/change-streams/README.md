# Run full text search queries on Amazon DocumentDB (with MongoDB compatibility) data with Amazon Elasticsearch Service

This repo is used for the blog post __[Run full text search queries on Amazon DocumentDB (with MongoDB compatibility) data with Amazon Elasticsearch Service] (https://aws.amazon.com/blogs/database/run-full-text-search-queries-on-amazon-documentdb-data-with-amazon-elasticsearch-service/)__

You can also use this sample solution to stream events to Amazon Managed Stream for Kafka (or any other Apache Kafka distro), AWS Kinesis Streams, AWS SQS, and S3. S3 streaming is done in micro-batches and the rest of the integration are near real-time.  

This sample solution is composed of:

## Lambda Function

The Lambda function retrieves Amazon DocumentDB credentials from Secrets Manager, sets up a connection to the Amazon DocumentDB cluster, reads the change events from the Amazon DocumentDB change stream, and replicates them to an Amazon ES indexes. The function also stores a change stream resume token in the Amazon DocumentDB cluster so it knows where to resume on its next run. To automate the solution, we poll for changes every 60 seconds. We use EventBridge to trigger a message to Amazon SNS, which invokes the function.

The Lambda function uses three variables that you can tune:

* Timeout – The duration after which the Lambda function times out. The default is set to 120 seconds. * Documents_per_run – The variable that controls how many documents to scan from the change stream with every function run. The default is set to 1000.
* Iterations_per_sync – The variable that determines how many iterations the Lambda function waits before syncing the resume token (the resume token to track the events processed in the change stream). The default is set to 15.

For target, there must be environment varibles in the lambda and permissions for the lambda role and/or network accordingly. 

Change Stream resumability was built around the resume token used within the watch api in options resumeAfter or startAfter. If there are not events when this Lambda function runs for the first time, it uses a canary to established a resume token for further executions.  

## SNS and EventBridge Rule

The sample solution will poll for changes every 120 seconds. It uses Amazon EventBridge to trigger a message to Amazon SNS, which will in turn invoke the AWS Lambda functions which does the bulk of the work.

# How to install

1. Enable __[change streams](https://docs.aws.amazon.com/documentdb/latest/developerguide/change-streams.html)__
2. Deploy a baseline environment. 
    1. Go to AWS CloudFormation in AWS console and select *Create stack*. 
    2. Check the *Upload a template file* option, select *Choose file *option and upload the __[change stream stack](https://raw.githubusercontent.com/aws-samples/amazon-documentdb-samples/master/samples/change-streams/setup/docdb_change_streams.yml)__ yaml file, and select *Next.*
    3. Give your stack a name, and input username, password, the identifier for your Amazon DocumentDB cluster. 
    4. AWS Cloud9 uses a Role. If you have used Cloud9 before, should already have an existing role. You can verify by going to the IAM console and searching for the role __[AWSCloud9SSMAccessRole](https://console.aws.amazon.com/iam/home?region=us-east-2#/roles/AWSCloud9SSMAccessRole)__. If you already have this role, choose true. If not, choose false and the AWS CloudFormation template creates this role for you. Select *Next.*  
    5. Leave everything as default and select *Next*. Check the box to allow the stack create a role on behalf of you and select *Create stack*. The stack should complete provisioning in a few minutes. 
3. Setup the Cloud9 environment
    1. From your AWS Cloud9 environment, launch a new tab to open the Preferences tab
    2. Select *AWS SETTINGS *from the left navigation pane
    3. Turn off *AWS managed temporary credentials. *This enables us to simplify the developer experience later in the walkthrough
    4. Close the Preferences tab 
    5. In a terminal window, execute 
        ```
        rm -vf ${HOME}/.aws/credentials
        ```
    6. Create an environment variable for the CloudFormation stack by executing: 
        ```
        export STACK=<Name of your CloudFormation stack> 
        echo "export STACK=${STACK}" >> ~/.bash_profile
        ```
    7. Configure AWS cli to use the current region as the default: 
        ```
        export AWS_REGION=$(curl -s 169.254.169.254/latest/dynamic/instance-identity/document | grep region | cut -d\" -f4)
        ```
    8. Execute the code below to update the environment libraries, upload streaming code to S3, and copy output from previous CloudFormation.
        ```
        curl -s https://raw.githubusercontent.com/aws-samples/amazon-documentdb-samples/master/samples/change-streams/setup/startup.sh -o startup.sh
        chmod 700 startup.sh
        ./startup.sh
        ```
7. Execute the commands below to create and deploy the AWS CloudFormation stack that will be populated with the required environment variables - Amazon DocumentDB URI, Amazon Elasticsearch service domain URI, watched database name, collection name, state database name, state collection name , networking configuration, SNS topics ARN, Lambda role ARN, and the Secrets Manager ARN.
    ```
    wget https://raw.githubusercontent.com/aws-samples/amazon-documentdb-samples/master/samples/change-streams/setup/lambda_function_config.sh
    chmod 700 lambda_function_config.sh
    ./lambda_function_config.sh
    ```
8. Streaming code is set. You can test it by running
    ```
    python test/es-test.py
    curl https://$(jq < cfn-output.json -r '.ElasticsearchDomainEndpoint')/_cat/indices?v
    ```

Once deployed, streaming functions will be run with the frequency set in the scheduling components. 

# Environment Varibles for targets
When you set up a target, make sure Lambda can reach it and the role associated to the lambda has proper permissions (e.g. s3:PutObject). 

To add new target, you just need to add a new environment variable to the Lambda streaming function. 

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