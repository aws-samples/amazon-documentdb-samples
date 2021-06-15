# Creating AWS Lambda Layer and deploying AWS CloudFormation Stack using AWS SAM CLI to create required infrastructure for Amazon DocumentDB to be used with AWS AppSync API

## Introduction

This example shows how to build AWS Lambda Layer, AWS Secrets manager, Amazon VPC and other infrastructure components, and Amazon Documentdb Cluster using AWS SAM CLI.
For more information on how to use this solution, refer to the [BLOG](https://aws.amazon.com/blogs/database/build-a-graphql-api-for-amazon-documentdb-with-mongodb-compatibility-using-aws-appsync/).

This project contains a AWS CloudFormation template and source code for the primary Lambda function and layer.

Important: This application uses various AWS services and there are costs associated with these services after the Free Tier usage - please see the [AWS Pricing page](https://aws.amazon.com/pricing/) for details. You are responsible for any AWS costs incurred. No warranty is implied in this example.

## Requirements

* An AWS account
* Permissions to create/modify AWS resources such as Amazon S3, Amazon VPC, Amazon DocumentDB, Amazon EC2 and Security Groups,AWS Secrets Manager,AWS IAM Policies and Roles,  AWS Lambda Function and Layer, AWS CloudFormation, AWS CLI, AWS SAM CLI.
* Familiarity with GraphQL, AWS Lambda, AWS Secrets Manager, Amazon DocumentDB 4.0 (with MongoDB compatibility), AWS IAM Policies and Roles, basic Git, Github operations.
* AWS CLI already configured with Administrator permission
* AWS SAM CLI installed - minimum version 0.48.
* Git Already installed and Configured
* [NodeJS 12.x installed](https://nodejs.org/en/download/),
refer to the [BLOG](https://aws.amazon.com/blogs/database/build-a-graphql-api-for-amazon-documentdb-with-mongodb-compatibility-using-aws-appsync/) prerequisites section for more details.

## Installation Instructions

1. On command prompt/terminal/Cloud9 environment Create a new directory, navigate to the directory
2. Clone the GIT repository with the CloudFormation template, Lambda Function code and Layer and other required files using below command

```bash
 git clone https://github.com/aws-samples/amazon-documentdb-samples.git
```
## Build

You need to build and package the .zip file for the Lambda layer that holds the database driver, certificate authority file to connect to Amazon DocumentDB
and nodejs modules required to run the lambda code. 
To do this, Navigate to the new folder blogs/appsync-docdb created by the above command  and run below

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
