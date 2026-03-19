import boto3
import os
import logging

# Set up the logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

## Set the following environment variable depending on which action the function should take
# ACTION = stop | start  

docdb_client = boto3.client('docdb')

def check_and_manage_docdb():
    action = os.environ.get('ACTION', 'stop').lower()

    if action == 'stop':
        stop_docdb_clusters()
    elif action == 'start':
        start_docdb_clusters()
    else:
        logger.error(f"Invalid action '{action}'. Valid options are 'stop' or 'start'.")


def stop_docdb_clusters():
    try:
        response = docdb_client.describe_db_clusters()
        for cluster in response["DBClusters"]:
            cluster_id = cluster["DBClusterIdentifier"]
            cluster_arn = cluster["DBClusterArn"]
            cluster_status = cluster["Status"]
            tags = docdb_client.list_tags_for_resource(ResourceName=cluster_arn)

            # Flag to track if the cluster is eligible to stop
            eligible_to_stop = False
            # Check tags for AllowStop
            for item in tags['TagList']:
                if item['Key'] == 'AllowStop' and item['Value'] == 'true':
                    eligible_to_stop = True
                    break

            if cluster_status == 'available' and eligible_to_stop:
                logger.info(f"{cluster_arn} is {cluster_status} and AllowStop tag is set to 'true'")
                logger.info(f"Stopping cluster: {cluster_arn}")
                stop_docdb = docdb_client.stop_db_cluster(DBClusterIdentifier=cluster_id)
                logger.info(stop_docdb)
            else:
                logger.debug(f"DocDB cluster {cluster_id} is {cluster_status}, but not eligible to stop, set the AllowStop tag accordingly.")
    except Exception as e:
        logger.error(f"An error occurred while stopping clusters: {str(e)}")


def start_docdb_clusters():
    try:
        response = docdb_client.describe_db_clusters()
        for cluster in response["DBClusters"]:
            cluster_id = cluster["DBClusterIdentifier"]
            cluster_arn = cluster["DBClusterArn"]
            cluster_status = cluster["Status"]
            tags = docdb_client.list_tags_for_resource(ResourceName=cluster_arn)
            
            # Flag to track if the cluster is eligible to start
            eligible_to_start = False
            # Check tags for AllowStart
            for item in tags['TagList']:
                if item['Key'] == 'AllowStart' and item['Value'] == 'true':
                    eligible_to_start = True
                    break
            
            if cluster_status == 'stopped' and eligible_to_start:
                logger.info(f"{cluster_arn} is {cluster_status} and AllowStart tag is set to 'true'")
                logger.info(f"Starting cluster: {cluster_arn}")
                start_docdb = docdb_client.start_db_cluster(DBClusterIdentifier=cluster_id)
                logger.info(start_docdb)
            else:
                logger.debug(f"DocDB cluster {cluster_id} is {cluster_status}, but not eligible to start, set the AllowStart tag accordingly.")
    except Exception as e:
        logger.error(f"An error occurred while starting clusters: {str(e)}")            


def lambda_handler(event, context):
    check_and_manage_docdb()
