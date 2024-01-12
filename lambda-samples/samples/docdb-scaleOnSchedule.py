import os
import boto3
import string
import random
import logging
import sys

# Set up the logger

logger = logging.getLogger()
logger.setLevel(logging.INFO)

clusterIdentifier = (os.environ["CLUSTER_IDENTIFIER"]).strip()
instanceClass = (os.environ["INSTANCE_CLASS"]).strip()
numInstancesToAdd = int(os.environ["INSTANCES_TO_ADD"])
numInstancesToDel = int(os.environ["INSTANCES_TO_DELETE"])

instancePromotionTier = 15
instanceSuffix = "tempinstance"

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
    "db.r5.16xlarge	",
    "db.r5.24xlarge",
    "db.t3.medium",
    "db.t4g.medium",
]


client = boto3.client("docdb")


def lambda_handler(event, context):

    ## Set the following Lambda event variable depending on which action the function should take
    # Action = Add | Delete

    if event["Action"] == "Add":
        actionResponse = add_instances()
    if event["Action"] == "Delete":
        actionResponse = delete_instances()

    logger.info(actionResponse)


def add_instances():

    createResponse = {}
    clusterInfo = client.describe_db_instances(
        Filters=[{"Name": "db-cluster-id", "Values": [clusterIdentifier]}]
    )
    listOfInstances = clusterInfo["DBInstances"]
    currInstanceCount = len(listOfInstances)

    if (
        currInstanceCount + numInstancesToAdd
    ) <= 16 and instanceClass in supportedInstanceClasses:

        for inst in range(numInstancesToAdd):
            randString = "".join(random.choices(string.ascii_lowercase, k=6))
            instanceIdentifier = instanceSuffix + "-" + randString

            try:
                instanceCreateResponse = client.create_db_instance(
                    DBClusterIdentifier=clusterIdentifier,
                    DBInstanceIdentifier=instanceIdentifier,
                    DBInstanceClass=instanceClass,
                    Tags=[{"Key": "scheduledTemporaryInstance", "Value": "Yes"}],
                    Engine="docdb",
                    PromotionTier=instancePromotionTier,
                )

                createResponse[instanceIdentifier] = instanceCreateResponse[
                    "ResponseMetadata"
                ]

            except:
                logger.error(
                    "Encountered problem while creating instance. Error message is %s %s",
                    sys.exc_info()[0],
                    sys.exc_info()[1],
                )

    elif (currInstanceCount + numInstancesToAdd) > 16:
        logger.info(
            "Cannot add more instances to the cluster "
            + clusterIdentifier
            + " already has  "
            + str(currInstanceCount)
            + " instances. "
            + "Adding "
            + str(numInstancesToAdd)
            + " instances exceeds the maximum number of allowed instances (16) in a cluster"
        )
    elif instanceClass not in supportedInstanceClasses:
        logger.info(instanceClass + " is not a supported instance class")

    return createResponse


def delete_instances():

    delResponse = {}
    instancesDeleted = {}
    instListToDelete = {}

    clusterInfo = client.describe_db_clusters(
        Filters=[{"Name": "db-cluster-id", "Values": [clusterIdentifier]}]
    )["DBClusters"]

    for clusterMembers in clusterInfo:
        instanceLists = clusterMembers["DBClusterMembers"]
        for instance in instanceLists:
            instanceDetails = client.describe_db_instances(
                DBInstanceIdentifier=instance["DBInstanceIdentifier"]
            )["DBInstances"]
            for instArn in instanceDetails:
                tags = client.list_tags_for_resource(
                    ResourceName=instArn["DBInstanceArn"]
                )["TagList"]

                for tag in tags:
                    if (
                        (
                            tag["Key"] == "scheduledTemporaryInstance"
                            and tag["Value"] == "Yes"
                        )
                        and instance["IsClusterWriter"] == False
                        and instance["DBInstanceIdentifier"].startswith(instanceSuffix)
                        and instArn["DBInstanceStatus"].lower() == "available"
                    ):

                        instListToDelete[instance["DBInstanceIdentifier"]] = instArn[
                            "DBInstanceArn"
                        ]

    if len(instListToDelete) >= numInstancesToDel:
        for instanceIdentifier in instListToDelete:
            delResponse = client.delete_db_instance(
                DBInstanceIdentifier=instanceIdentifier
            )
            instancesDeleted[instanceIdentifier] = delResponse["ResponseMetadata"]
            if len(instancesDeleted) >= numInstancesToDel:
                return instancesDeleted
    else:
        return "No Amazon DocumentDB instances found matching the delete criteria"
