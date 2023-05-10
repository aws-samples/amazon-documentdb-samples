import boto3
import json
import os

description_list=['Bug Fixes']
action_list=['db-upgrade']
notification = "This is notification for Aurora and DocumentDB patch \n"

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
                if mw_description not in description_list and mw_action not in action_list:
                    num = num - 1
                    continue
                temp_string = "**********************************************" +  "\n"
                notification += temp_string
                temp_string = "Region: " + REGION['RegionName'] +  " has Aurora or docDB cluster needed to be upgrade.\n"
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
def lambda_handler(event, context):
    global notification
    sns_client = boto3.client('sns')
    query_docdb()
    print (notification)
    sns_arn = os.environ.get('SNS_TOPIC_ARN')

    sns_response = sns_client.publish (
        TargetArn = sns_arn,
        Subject = "DocumentDB Patch Notification",
        Message = json.dumps({'default': notification}),
        MessageStructure = 'json'
     )
