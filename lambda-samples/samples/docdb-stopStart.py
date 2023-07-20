import boto3
import os

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
        print(f"Invalid action '{action}'. Valid options are 'stop' or 'start'.")

def stop_docdb_clusters():
    response = docdb_client.describe_db_clusters()
    for cluster in response["DBClusters"]:
        cluster_id = cluster["DBClusterIdentifier"]
        cluster_arn = cluster["DBClusterArn"]
        cluster_status = cluster["Status"]
        tags = docdb_client.list_tags_for_resource(ResourceName=cluster_arn)
        if cluster_status == 'available':
            # Get tags to stop only clusters with the AllowStop tag
            for item in tags['TagList']:
                if item['Key'] == 'AllowStop' and item['Value'] == 'true':
                    print(f"{cluster_arn} is {cluster_status} and AllowStop is {item['Value']}")
                    print(f"Stopping cluster: {cluster_arn}")
                    stop_docdb = docdb_client.stop_db_cluster(DBClusterIdentifier=cluster_id)
                    print(stop_docdb)
        else:
            print(f"DocDB cluster {cluster_id} is not eligible to stop, set the AllowStop tag accordingly!")

def start_docdb_clusters():
    response = docdb_client.describe_db_clusters()
    for cluster in response["DBClusters"]:
        cluster_id = cluster["DBClusterIdentifier"]
        cluster_arn = cluster["DBClusterArn"]
        cluster_status = cluster["Status"]
        tags = docdb_client.list_tags_for_resource(ResourceName=cluster_arn)
        if cluster_status == 'stopped':
            # Get tags to start only clusters with the AllowStart tag
            for item in tags['TagList']:
                if item['Key'] == 'AllowStart' and item['Value'] == 'true':
                    print(f"{cluster_arn} is {cluster_status} and AllowStart is {item['Value']}")
                    print(f"Starting cluster: {cluster_arn}")
                    start_docdb = docdb_client.start_db_cluster(DBClusterIdentifier=cluster_id)
                    print(start_docdb)
        else:
            print(f"DocDB cluster {cluster_id} is not eligible to start, set the AllowStart tag accordingly!")

def lambda_handler(event, context):
    check_and_manage_docdb()
