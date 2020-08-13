#!/bin/bash

# Update instance and install packages
sudo yum update -y
sudo yum install -y jq moreutils

# Create target dir and download AES sample template
mkdir target
cd target
wget https://raw.githubusercontent.com/aws-samples/amazon-documentdb-samples/master/samples/change-streams/targets/elasticsearch-sample.json

# Set ACCOUNT_ID and AWS_REGION
export ACCOUNT_ID=$(aws sts get-caller-identity --output text --query Account)
export AWS_REGION=$(curl -s 169.254.169.254/latest/dynamic/instance-identity/document | \
  grep region | cut -d\" -f4)

# Replace region and account
replace awsregion "'$AWS_REGION'" -- elasticsearch-sample.json
replace accountid "'$ACCOUNT_ID'" -- elasticsearch-sample.json 