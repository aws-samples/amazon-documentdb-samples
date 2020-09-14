#!/bin/bash

if [ -n "$STACK" ]
then
    echo 'Upgrading/Installing libraries and packages'
    # Update instance and install packages
    echo -e "[mongodb-org-3.6] \nname=MongoDB Repository\nbaseurl=https://repo.mongodb.org/yum/amazon/2013.03/mongodb-org/3.6/x86_64/\ngpgcheck=1 \nenabled=1 \ngpgkey=https://www.mongodb.org/static/pgp/server-3.6.asc" | sudo tee /etc/yum.repos.d/mongodb-org-3.6.repo
    sudo yum update -y
    sudo yum install -y jq moreutils
    sudo yum install -y mongodb-org-shell
    sudo python -m pip install pymongo
    wget https://s3.amazonaws.com/rds-downloads/rds-combined-ca-bundle.pem

    # Upgrade pip
    sudo pip3 install --upgrade pip
    echo "export PATH=~/.local/bin:$PATH" >> ~/.bash_profile
    source ~/.bash_profile

    # Upgrade awscli
    pip3 install awscli --upgrade --user
    source ~/.bash_profile

    echo 'Setting up the AWS REGION'
    # Setting up the AWS REGION
    echo "export AWS_REGION=${AWS_REGION}" >> ~/.bash_profile
    aws configure set default.region ${AWS_REGION}

    echo 'Getting the CloudFormation template for the Lambda streaming function'
    # Get the AWS CloudFormation solution
    wget https://raw.githubusercontent.com/aws-samples/amazon-documentdb-samples/master/samples/change-streams/app/change_streams_stack.yml

    echo 'Copy output from CloudFormation to your workspace into file cfn-output.json'
    # Upload Lambda Code
    aws cloudformation describe-stacks --stack-name $STACK | jq -r '[.Stacks[0].Outputs[] | {key: .OutputKey, value: .OutputValue}] | from_entries' > cfn-output.json

    echo 'Packaging and uploading streaming code to S3'
    # Upload Lambda Code
    cd..
    mkdir app && cd app
    wget https://raw.githubusercontent.com/aws-samples/amazon-documentdb-samples/master/samples/change-streams/app/lambda_function.py
    wget https://raw.githubusercontent.com/aws-samples/amazon-documentdb-samples/master/samples/change-streams/app/requirements.txt
    python -m venv repLambda
    source repLambda/bin/activate
    mv lambda_function.py repLambda/lib/python*/site-packages/
    mv requirements.txt repLambda/lib/python*/site-packages/
    cd repLambda/lib/python*/site-packages/
    pip install -r requirements.txt 
    deactivate
    mv ../dist-packages/* .
    zip -r9 repLambdaFunction.zip .
    aws s3 cp repLambdaFunction.zip s3://$(aws cloudformation describe-stacks --stack-name $STACK | jq -r '[.Stacks[0].Outputs[] | {key: .OutputKey, value: .OutputValue}] | from_entries'.S3BucketName)

else
  echo "Remind to create an environment variable for your stack name. It is done in a step above."
fi