import json
import os
import boto3
import sys
import logging

# Set up the logger

logger = logging.getLogger()
logger.setLevel(logging.INFO)

clusterIdentifier = os.environ["CLUSTER_ID"].strip()
instanceIdentifier = os.environ["INSTANCE_NAME"].strip()
instanceClass = os.environ["INSTANCE_CLASS"].strip()
instancePromotionTier = 15
supportedInstanceClasses = [
    "db.r6g.large",
    "db.r6g.xlarge",
    "db.r6g.2xlarge",
    "db.r6g.4xlarge",
    "db.r6g.8xlarge",
    "db.r6g.12xlarge",
    "db.r6g.16xlarge",
    "db.r5.large",
    "db.r5.xlarge",
    "db.r5.2xlarge",
    "db.r5.4xlarge",
    "db.r5.8xlarge",
    "db.r5.12xlarge",
    "db.r5.16xlarge",
    "db.r5.24xlarge",
    "db.t3.medium",
    "db.t4g.medium"
]

client = boto3.client("docdb")

## Set the following Lambda event variable depending on which action the function should take
# Action = Add | Delete


def lambda_handler(event, context):
    if event["Action"] == "Add":
        add_instances()
    if event["Action"] == "Delete":
        delete_instances()


def add_instances():

    instanceNotExisits = True
    createResponse = None
    instDetails = []

    clusterInfo = client.describe_db_instances(
        Filters=[{"Name": "db-cluster-id", "Values": [clusterIdentifier]}]
    )
    listOfInstances = clusterInfo["DBInstances"]
    currInstanceCount = len(listOfInstances)
    for instance in listOfInstances:
        instDetails.append(instance["DBInstanceIdentifier"])
    try:
        if instanceIdentifier.lower() in instDetails:
            instanceNotExisits = False
            print(instanceNotExisits, clusterIdentifier, instanceIdentifier)
            raise ValueError(
                instanceIdentifier
                + " already exist in the cluster "
                + clusterIdentifier
            )
        if (
            instanceNotExisits
            and ((currInstanceCount + 1) <= 16)
            and instanceClass in supportedInstanceClasses
        ):

            createResponse = client.create_db_instance(
                DBClusterIdentifier=clusterIdentifier,
                DBInstanceIdentifier=instanceIdentifier,
                DBInstanceClass=instanceClass,
                Tags=[{"Key": "TemporaryInstance", "Value": "Yes"}],
                Engine="docdb",
                PromotionTier=instancePromotionTier,
            )

            logger.info(
                "Instance "
                + instanceIdentifier
                + " is in "
                + createResponse["DBInstance"]["DBInstanceStatus"]
                + " state and StatusCode is "
                + str(createResponse["ResponseMetadata"]["HTTPStatusCode"])
            )

            return createResponse["ResponseMetadata"]

        elif (currInstanceCount + 1) > 16:
            logger.info(
                "Cannot add more instances to the cluster "
                + clusterIdentifier
                + " already has  "
                + str(currInstanceCount)
                + " instances. "
                + "Adding more instances exceeds the maximum number of allowed instances (16) in a cluster"
            )

        elif instanceClass not in supportedInstanceClasses:
            logger.info(instanceClass + " is not a supported instance class")

    except:
        logger.error(
            "Encountered problem while creating instance. Error message is %s %s",
            sys.exc_info()[0],
            sys.exc_info()[1],
        )


def delete_instances():
    instDetails = []
    delResponse = None
    resp = {}
    
    clusterId = clusterIdentifier
    instanceIdentifierToDel = instanceIdentifier
   

    client = boto3.client("docdb")
    clusterInfo = client.describe_db_instances(
        Filters=[{"Name": "db-cluster-id", "Values": [clusterId]}]
    )
    listOfInstances = clusterInfo["DBInstances"]
    for instance in listOfInstances:
        instDetails.append(instance["DBInstanceIdentifier"])
    try:
        if instanceIdentifierToDel.lower() not in instDetails:
            raise ValueError(instanceIdentifierToDel + " does not exist")
        else:
            delResponse = client.delete_db_instance(
                DBInstanceIdentifier=instanceIdentifierToDel
            )
            resp["StatusCode"] = delResponse["ResponseMetadata"]["HTTPStatusCode"]
            resp["Instance"] = delResponse["DBInstance"]["DBInstanceIdentifier"]
            resp["CurrentState"] = delResponse["DBInstance"]["DBInstanceStatus"]
            logger.info(
                "Instance "
                + instanceIdentifierToDel
                + " is in "
                + resp["CurrentState"]
                + " state and StatusCode is "
                + str(resp["StatusCode"])
            )
        return resp

    except:
        logger.error(
            "Encountered problem while trying to delete instance. Error message is %s %s",
            sys.exc_info()[0],
            sys.exc_info()[1],
        )
