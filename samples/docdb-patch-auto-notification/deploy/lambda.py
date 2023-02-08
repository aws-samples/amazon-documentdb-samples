import boto3
import json

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
                mw_type=inst['PendingMaintenanceActionDetails'][0]['Description']
                if mw_type != 'Bug Fixes':
                    num = num - 1
                    continue
                temp_string = "Region: " + REGION['RegionName'] +  " has docDB cluster needed to be upgrade.\n"
                notification += temp_string
                temp_string = "The Cluster has pending maintenance action: " + inst['ResourceIdentifier'] + "\n"
                notification += temp_string
                cls_identifier=inst['ResourceIdentifier'].split(':')[-1]
                try:
                    cls = docDB.describe_db_clusters(DBClusterIdentifier=cls_identifier)
                except Exception as e:
                        temp_string = "Failed to get cluster information " + cls_identifier + " Exception: " + e + "\n"
                        notification += temp_string
                        continue
                dbclus=cls['DBClusters']
                mw = dbclus[0]['PreferredMaintenanceWindow']
                temp_string = "The Cluster maintenance window UTC time: " + mw + "\n"
                notification += temp_string
            temp_string = "Region: " + REGION['RegionName'] + " has total " + str(num) + " cluster found.\n"   
            notification += temp_string
        else:
            temp_string = "Region: " + REGION['RegionName'] + " No Cluster found.\n"
            notification += temp_string
def lambda_handler(event, context):
    global notification
    sns_client = boto3.client('sns')
    query_docdb()
    print (notification)
    sns_response = sns_client.publish (
        TargetArn = "arn:aws:sns:us-east-1:02818****:docdb-patch-notification",
        Subject = "DocumentDB Patch Notification",
        Message = json.dumps({'default': notification}),
        MessageStructure = 'json'
     )
