import boto3
import os

target_cluster = None
docdb = boto3.client('docdb')

def get_tags_for_db_cluster(db):
    cluster_arn = db['DBClusterArn']
    cluster_tags = docdb.list_tags_for_resource(ResourceName=cluster_arn)
    return cluster_tags['TagList']

def lambda_handler(event, context):

    dbs = docdb.describe_db_clusters()
    
    for db in dbs['DBClusters']:
        cluster_id = db['DBClusterIdentifier']
        print('Cluster name: ' + str(cluster_id))
        db_tags = get_tags_for_db_cluster(db)
        print("Cluster tags: " + str(db_tags))
        tag = next(iter(filter(lambda tag: tag['Key'] == 'AutoStart' and tag['Value'].lower() == 'true', db_tags)), None)
        print("AutoStart tag: " + str(tag))

        if tag:
            target_cluster = db
            cluster_status = target_cluster['Status']
            print("Cluster status: " + str(cluster_status))
            cluster_id = target_cluster['DBClusterIdentifier']
            if cluster_status == "stopped":
                AutoStarting = docdb.start_db_cluster(DBClusterIdentifier=cluster_id)
                print("Starting cluster: " + str(cluster_id))
            else:
                print("Cluster " + str(cluster_id) + " is already available.")
        else:
            print("Missing 'AutoStart' Tag on cluster; skipping...")