#!/bin/bash

# Update instance and install packages
sudo yum update -y
sudo yum install -y jq moreutils

# Upgrade pip
sudo pip3 install --upgrade pip
echo "export PATH=~/.local/bin:$PATH" >> ~/.bash_profile
source ~/.bash_profile

# Upgrade awscli
pip3 install awscli --upgrade --user
source ~/.bash_profile

# Update node
nvm install node
source ~/.bash_profile

# Install CDK
npm install -g aws-cdk --force
source ~/.bash_profile

# creates a project folder
mkdir change-streams-project && cd change-streams-project

# Create cdk project
cdk init app --language python

# Activate Python virtual environment
source .env/bin/activate

# Set ACCOUNT_ID and AWS_REGION
export ACCOUNT_ID=$(aws sts get-caller-identity --output text --query Account)
export AWS_REGION=$(curl -s 169.254.169.254/latest/dynamic/instance-identity/document | \
  grep region | cut -d\" -f4)

# Replace values in app.py
sed -i 's/streams-project"/streams-project",env={"region": awsregion,"account":accountid}/' app.py
replace awsregion "'$AWS_REGION'" -- app.py
replace accountid "'$ACCOUNT_ID'" -- app.py  

# Install dependencies 
pip install -r requirements.txt
pip install aws-cdk.aws-lambda
pip install aws-cdk.aws-sns
pip install aws-cdk.aws-lambda-event-sources

# Create SNS topics to be used in the solution
cd ..
export SNS_TRIGGER=$(aws sns create-topic --name sns_changestreams_trigger | jq -r .'TopicArn')
export SNS_ALERT=$(aws sns create-topic --name sns_changestreams_alert | jq -r .'TopicArn')

# Download Lambda rol template, replace variables, and create role
wget 
replace [SecretARN] "$DOCDB_CREDENTIALS" -- lambdaRole.json
replace [TopicARN] "$SNS_TRIGGER" -- lambdaRole.json   
export CS_POLICY=$(aws iam create-policy --policy-name policy-change-streams --policy-document file://lambdaRole.json | jq -r .'Policy'.'Arn')
wget 
export ROLE=$(aws iam create-role --role-name role-change-streams --assume-role-policy-document file://trustPolicy.json | jq -r .'Role'.'Arn') 
aws iam attach-role-policy --policy-arn $CS_POLICY --role-name role-change-streams

# Download config file for the CDK project
cd change-streams-project
wget https://raw.githubusercontent.com/aws-samples/amazon-documentdb-samples/master/samples/change-streams/cdk/config.ini
replace [TopicARNAlert] "$SNS_ALERT" -- config.ini
replace [TopicARNTrigger] "$SNS_TRIGGER" -- config.ini
replace [ARNRole] "$ROLE" -- config.ini

# Replace code of template CDK project with the one in GitHub
wget https://raw.githubusercontent.com/aws-samples/amazon-documentdb-samples/master/samples/change-streams/cdk/change_streams_project_stack.py -O change_streams_project/change_streams_project_stack.py

# Upload Lambda Code
mkdir app
cd ../app
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
aws s3 cp repLambdaFunction.zip s3://$S3_BUCKET