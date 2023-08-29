import boto3
import json
import os

action_list=['system-update']
notification = "This is notification for DocumentDB patch \n"

def query_docdb():
    global notification
    EC2 = boto3.client('ec2')
    regions = EC2.describe_regions()
   
    for REGION in regions['Regions']:
        docDB = boto3.client('docdb',REGION['RegionName'])
        pma = docDB.describe_pending_maintenance_actions()
        if len(pma['PendingMaintenanceActions']) > 0:
            num = len(pma['PendingMaintenanceActions'])
            for inst in pma['PendingMaintenanceActions']:
                mw_description=inst['PendingMaintenanceActionDetails'][0]['Description']
                mw_action=inst['PendingMaintenanceActionDetails'][0]['Action']
                if mw_action not in action_list:
                    num = num - 1
                    continue
                if not pending_action_is_docdb_cluster_engine_patch(docDB, inst):
                    num = num - 1
                    continue    
                temp_string = "**********************************************" +  "\n"
                notification += temp_string
                temp_string = "Region: " + REGION['RegionName'] +  " has  docDB cluster needed to be upgrade.\n"
                notification += temp_string
                temp_string = "Mw_description: " + mw_description +  "\n"
                notification += temp_string
                temp_string = "Mw_action: " + mw_action +  "\n"
                notification += temp_string
                temp_string = "The Resource has pending maintenance action: " + inst['ResourceIdentifier'] + "\n"
                notification += temp_string
                cls_identifier=inst['ResourceIdentifier'].split(':')[-1]
                try:
                    cls = docDB.describe_db_clusters(DBClusterIdentifier=cls_identifier)
                except Exception as e:
                        temp_string = "Failed to get cluster information! This is instance level notification" + "\n" 
                        notification += temp_string
                        temp_string = "**********************************************" +  "\n"
                        notification += temp_string
                        continue
                dbclus=cls['DBClusters']
                mw = dbclus[0]['PreferredMaintenanceWindow']
                temp_string = "The Cluster maintenance window UTC time: " + mw + "\n"
                notification += temp_string
            temp_string = "Region: " + REGION['RegionName'] + " has total " + str(num) + " resource found.\n"   
            notification += temp_string
            temp_string = "**********************************************" +  "\n"
            notification += temp_string
        else:
            temp_string = "Region: " + REGION['RegionName'] + " No Cluster found.\n"
            notification += temp_string
def pending_action_is_docdb_cluster_engine_patch(docdb_client, pending_action):
    """
    For a pending maintenance action to be a DocumentDB cluster engine patch, ALL of the following MUST be true:
    
    1. The ARN of the pending maintenance action is for a 'cluster'
        * Ex. arn = "arn:aws:rds:us-east-1:000123456789:cluster:test-cluster-1"
    2. The 'action' of a pending maintenance action must be type 'system-update'
        * Ex. action = {..., "Action": "system-update", ...}
    3. The "Engine" of the DB cluster must be "docdb"
    """
    # 1
    pending_action_resource_arn = pending_action['ResourceIdentifier']
    if pending_action_resource_arn.split(":")[5] != "cluster":
        return False
    # 2
    action_type = pending_action['PendingMaintenanceActionDetails'][0].get('Action')
    if action_type != "system-update":
        return False
    # 3 
    cluster_identifier = pending_action_resource_arn.split(":")[6]
    describe_db_cluster_response = docdb_client.describe_db_clusters(DBClusterIdentifier=cluster_identifier)
    if describe_db_cluster_response["DBClusters"][0]["Engine"] != "docdb":
        return False
    return True     

def lambda_handler(event, context):
    global notification
    sns_client = boto3.client('sns')
    query_docdb()
    print (notification)
    sns_arn = os.environ.get('SNS_TOPIC_ARN')

    sns_response = sns_client.publish (
        TargetArn = sns_arn,
        Subject = "Database Patch Notification",
        Message = json.dumps({'default': notification}),
        MessageStructure = 'json'
     )
