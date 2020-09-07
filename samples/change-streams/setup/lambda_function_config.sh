#!/bin/bash

# Replace values from the baseline CloudFormation 
replace [S3BUCKET_CFN] $(jq < cfn-output.json -r '.S3BucketName') -- change_streams_stack.yml 
replace [ARN_ROLE_CFN] $(jq < cfn-output.json -r '.RoleArn') -- change_streams_stack.yml 
replace [DOCDB_SECRETSMAN_NAME_CFN] $(jq < cfn-output.json -r '.DocDBSecretName') -- change_streams_stack.yml 
replace [DOCDB_URI_CFN] $(jq < cfn-output.json -r '.DocumentDBEndpoint') -- change_streams_stack.yml 
replace [SNS_TOPIC_ARN_ALERT_CNF] $(jq < cfn-output.json -r '.SNSTopicAlert') -- change_streams_stack.yml 
replace [ELASTICSEARCH_URI_CFN] $(jq < cfn-output.json -r '.ElasticsearchDomainEndpoint') -- change_streams_stack.yml 
replace [DOCDB_SG_CFN] $(jq < cfn-output.json -r '.DocumentDBSecurityGroup') -- change_streams_stack.yml 
replace [ELASTICSEARCH_SG_CFN] $(jq < cfn-output.json -r '.ElasticsearchSecurityGroup') -- change_streams_stack.yml 
replace [SUBNET_ONE_CFN] $(jq < cfn-output.json -r '.PrivateSubnetOne') -- change_streams_stack.yml 
replace [SUBNET_TWO_CFN] $(jq < cfn-output.json -r '.PrivateSubnetTwo') -- change_streams_stack.yml 
replace [SUBNET_THREE_CFN] $(jq < cfn-output.json -r '.PrivateSubnetThree') -- change_streams_stack.yml 
replace [SNS_TOPIC_ARN_TRIGGER_CNF] $(jq < cfn-output.json -r '.SNSTopicTrigger') -- change_streams_stack.yml 