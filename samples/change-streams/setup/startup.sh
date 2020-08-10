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
aws s3 cp repLambdaFunction.zip $S3_BUCKET