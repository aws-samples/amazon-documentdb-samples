#!/bin/bash

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

# Download config file for the CDK project   ************************************************
cd change-streams-project
wget https://raw.githubusercontent.com/aws-samples/amazon-documentdb-samples/master/samples/change-streams/cdk/config.ini

# Replace code of template CDK project with the one in GitHub
wget https://raw.githubusercontent.com/aws-samples/amazon-documentdb-samples/master/samples/change-streams/cdk/change_streams_project_stack.py -O change_streams_project/change_streams_project_stack.py

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
aws s3 cp repLambdaFunction.zip s3://$S3_BUCKET