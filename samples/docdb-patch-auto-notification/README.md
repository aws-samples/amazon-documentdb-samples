# Build serverless automatic email notification for Amazon DocumentDB, Amazon Aurora, and Amazon Neptune patch events 

## Introduction
Amazon DocumentDB (with MongoDB compatibility), Amazon Aurora, and Amazon Neptune are scalable, highly durable, and fully managed cloud-native document, relational, and graph databases for operating mission-critical workloads that simplify the process of setting up, managing operations, and scaling databases in the cloud.

Periodically, Amazon DocumentDB, Aurora, and Neptune perform maintenance on resources. Maintenance most often involves updates to the DB cluster's underlying hardware, operating system (OS), or database engine version. It is necessary to apply database patches in a timely manner and update the OS or database engine version to better protect your cloud database.

For security and instance reliability, Amazon DocumentDB, Aurora, and Neptune require your DB clusters to do required OS or database patching as part of certain maintenance projects. Such patching occurs infrequently (typically once every few months) and seldom requires more than a fraction of your maintenance window. 

we introduce a serverless solution to get notification when a required patch is scheduled for your cluster. 


To accomplish solution goal, we use the following services:

1. AWS Lambda: Deploy a Lambda function to query scheduled patches of Amazon DocumentDB, Aurora and Neptune
2. Amazon EventBridge: Schedule the Lambda function run one time a day
3. Amazon SNS:Send email notification for scheduled Amazon DocumentDB, Aurora and Neptune patches

We use the AWS Serverless Application Model (AWS SAM) to deploy this stack because it is the preferred approach when developing serverless applications such as this one. 


## Requirements

    1. Amazon EC2 Linux 2 Bastion Host
    2. AWS CLI already configured with Administrator permission
    3. AWS SAM CLI installed 
    4. Git Already installed and Configured
    5. Python 3.10 installed


## Inputs
The following are the inputs to the SAM template:
- Stack Name
- EmailAddress for receiving email


## Build
To validate the SAM template run:

```
sam validate
```

To build the SAM template run:

```
sam build
```

or 

```
make build
```

## Deploy
To deploy, run

```
sam deploy --capabilities CAPABILITY_NAMED_IAM --guided
```

or 

```
make sam
```



