# Creating Lambda Layer and deploying CloudFormation Stack using SAM CLI to create required infrastructure for Amazon DocumentDB to be used with AWS AppSync API

## Introduction

This example shows how to build Lambda Layer, Secrets manager, VPC and other infrastructure components, and Documentdb Cluster using SAM CLI.
For more information on how to use this solution, refer to the BLOG.

This project contains a SAM template and source code for the primary Lambda function, .

Important: this application uses various AWS services and there are costs associated with these services after the Free Tier usage - please see the [AWS Pricing page](https://aws.amazon.com/pricing/) for details. You are responsible for any AWS costs incurred. No warranty is implied in this example.

## Requirements

* An [AWS account](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html) 
* Permissions to create/modify AWS resources such as S3, VPC, Amazon DocumentDB, EC2 and Security Groups, Secrets Manager, IAM Policies and Roles, Lambda Function and Lambda Layer, CloudFormation, AWS CLI.
* Familiarity with GraphQL, AWS Lambda, AWS Secrets Manager, Amazon DocumentDB 4.0 (with MongoDB compatibility), AWS IAM Policies and Roles, basic Git, Github operations.
* AWS CLI already configured with Administrator permission
* [AWS SAM CLI installed](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) - minimum version 0.48.
* Git Already installed and Configured
* [NodeJS 12.x installed](https://nodejs.org/en/download/)

## Installation Instructions

1. On command prompt/terminal/Cloud9 environment Create a new directory, navigate to the directory
2. Clone the GIT repository with the CloudFormation template, Lambda Function code and Layer and other required files using below command

```bash
 git clone https://github.com/aws-samples/appsync-docdb.git
```

## Build

You need to build and package the .zip file for the Lambda layer that holds the database driver, certificate authority file to connect to Amazon DocumentDB
and nodejs modules required to run the lambda code. 
To do this, Navigate to the new folder appsync-docdb created by the above command  and run

```bash
make
```

### Inputs

The following are the inputs to the SAM template:

- Stack Name
- AWS Region (use one of ap-south-1,us-east-1,us-west-1,ca-central-1,eu-west-1,eu-central-1,ap-southeast-1)
- Password for Amazon DocumentDB (to be stored in Secrets Manager)

### Deploy

To deploy, run

```bash
sam deploy --capabilities CAPABILITY_NAMED_IAM --guided
```

And follow the prompts.

## Next steps

The AWS Appsync Document DB Blog post at the top of this README file contains additional information on the how to continue using this infrastructure to create AWS AppSync API.
