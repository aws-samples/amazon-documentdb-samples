import configparser
import ast
from aws_cdk import (
    core, 
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_sns as sns,
    aws_lambda_event_sources as sources,
)
# config file load
config = configparser.ConfigParser()
config.read('config.ini')  

class ChangeStreamsProjectStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:

        super().__init__(scope, id, **kwargs)

        # set role object
        role = iam.Role.from_role_arn(self, "Role", config['control']['roleArn'],mutable=False)   

        # Get Lambda code
        lambda_code_bucket = s3.Bucket.from_bucket_attributes(
            self, 'LambdaCodeBucket',
            bucket_name=config['control']['bucket']
        )

        # set vpc object
        vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_id=config['network']['vpc_id'])

        # set subnets object
        ec2_subnets = []
        for i in ast.literal_eval(config['network']['subnets']):
            ec2_subnets.append(ec2.Subnet.from_subnet_attributes(self, str(i['subnet']), subnet_id=str(i['subnet']), 
                availability_zone=str(i['az'])))
        snSelection = ec2.SubnetSelection(subnets=ec2_subnets)

        # set subnets object
        ec2_sgs = []
        for j in ast.literal_eval(config['network']['securityGroups']):
            ec2_sgs.append(ec2.SecurityGroup.from_security_group_id(self, str(j), security_group_id=str(j)))

        # Get SNS ARN
        sns_topic = sns.Topic.from_topic_arn(self, "sns_topic", topic_arn=config['control']['sns_trigger'])

        # Build lambdas
        for x in ast.literal_eval(config['collections']['endpoints_dbs_col']):
            for y in x['cols']:
                lambdaFn = _lambda.Function(
                    self, 'replicator'+str(x['db'])+str(y),
                    runtime=_lambda.Runtime.PYTHON_3_7,
                    code = _lambda.S3Code(bucket=lambda_code_bucket,key=config['control']['key']),
                    handler = 'lambda_function.lambda_handler',
                    description = 'Lambda used to replicate changes on database: ' + str(x['db']) + ' collection: ' + str(y),
                    environment = dict(
                        DOCUMENTDB_SECRET=config['endpoints']['docdb_secret_name'],
                        DOCUMENTDB_URI=config['endpoints']['docdb_uri']+':27017',
                        MAX_LOOP=config['control']['maxloop'],
                        SNS_TOPIC_ARN_ALERT=config['control']['sns_alert'],
                        STATE_COLLECTION=config['endpoints']['statecol'],
                        STATE_DB=config['endpoints']['statedb'],
                        STATE_SYNC_COUNT=config['control']['sync'],
                        WATCHED_COLLECTION_NAME=str(y),
                        WATCHED_DB_NAME=str(x['db']),
                        #ELASTICSEARCH_URI='https://'+config['endpoints']['elasticsearch_uri'],
                        #BUCKET_NAME=config['endpoints']['bucket'],
                        #BUCKET_PATH=config['endpoints']['path'],
                        #MSK_BOOTSTRAP_SRV=config['endpoints']['kafka_boostrap'],
                        #SNS_TOPIC_ARN_EVENT=config['endpoints']['sns_topic'],
                        #KINESIS_STREAM=config['endpoints']['kinesis_stream'],
                        #SQS_QUERY_URL=config['endpoints']['sqs_query_url'],
                    ),
                    function_name = 'docdb-cdc-'+str(x['db'])+'-'+str(y),
                    role = role,
                    security_groups = ec2_sgs,
                    timeout = core.Duration.seconds(config['control'].getint('lambdaTimeout')),
                    vpc = vpc,
                    vpc_subnets = snSelection,
                    memory_size = config['control'].getint('lambdaMemory'),
                )

                lambdaFn.add_event_source(sources.SnsEventSource(sns_topic))