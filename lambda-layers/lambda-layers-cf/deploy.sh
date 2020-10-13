#!/bin/bash

: "${AWS_ACCESS_KEY_ID:?Need to set AWS_ACCESS_KEY_ID non-empty}"
: "${AWS_SECRET_ACCESS_KEY:?Need to set AWS_SECRET_ACCESS_KEY non-empty}"
: "${AWS_DEFAULT_REGION:?Need to set AWS_DEFAULT_REGION non-empty}"
: "${DYNAMODB_SNS_EMAIL:?Need to set DYNAMODB_SNS_EMAIL to valid email address}"

EMAIL_REGEX="^[a-z0-9!#\$%&'*+/=?^_\`{|}~-]+(\.[a-z0-9!#$%&'*+/=?^_\`{|}~-]+)*@([a-z0-9]([a-z0-9-]*[a-z0-9])?\.)+[a-z0-9]([a-z0-9-]*[a-z0-9])?\$"
STACK_NAME=dynamodb-monitoring

if [[ ! $DYNAMODB_SNS_EMAIL =~ $EMAIL_REGEX ]] ; then
    echo "Need to set DYNAMODB_SNS_EMAIL to valid email address"
    exit 1
fi

# I coudln't figure out a way to put most of the variables in a params file and still pass in the email parameter from the environment
#  If anybody knows a way, it would be nice to know.
if ! aws cloudformation describe-stacks --stack-name $STACK_NAME > /dev/null 2>&1; then
    aws cloudformation create-stack --stack-name $STACK_NAME --template-body file:///tmp/src/dynamodb_alarms_cf/dynamodb_alarms_cf.yaml --parameters \
        ParameterKey=DynamoDBProvisionedTableName,ParameterValue=dynamodb-provisioned-monitoring \
        ParameterKey=DynamoDBOnDemandTableName,ParameterValue=dynamodb-ondemand-monitoring \
        ParameterKey=DynamoDBGlobalTableName,ParameterValue=dynamodb-gt-monitoring \
        ParameterKey=DynamoDBGlobalTableReceivingRegion,ParameterValue=us-west-2 \
        ParameterKey=DynamoDBStreamLambdaFunctionName,ParameterValue=FooDataForwardToKinesis \
        ParameterKey=DynamoDBCustomNamespace,ParameterValue=Custom_DynamoDB \
        ParameterKey=DynamoDBSNSEmail,ParameterValue=$DYNAMODB_SNS_EMAIL \
        --capabilities CAPABILITY_IAM
else
    aws cloudformation update-stack --stack-name $STACK_NAME --template-body file:///tmp/src/dynamodb_alarms_cf/dynamodb_alarms_cf.yaml --parameters \
        ParameterKey=DynamoDBProvisionedTableName,ParameterValue=dynamodb-provisioned-monitoring \
        ParameterKey=DynamoDBOnDemandTableName,ParameterValue=dynamodb-ondemand-monitoring \
        ParameterKey=DynamoDBGlobalTableName,ParameterValue=dynamodb-gt-monitoring \
        ParameterKey=DynamoDBGlobalTableReceivingRegion,ParameterValue=us-west-2 \
        ParameterKey=DynamoDBStreamLambdaFunctionName,ParameterValue=FooDataForwardToKinesis \
        ParameterKey=DynamoDBCustomNamespace,ParameterValue=Custom_DynamoDB \
        ParameterKey=DynamoDBSNSEmail,ParameterValue=$DYNAMODB_SNS_EMAIL \
        --capabilities CAPABILITY_IAM
fi
