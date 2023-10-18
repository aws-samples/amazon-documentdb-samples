import boto3
import time
import logging
import sys
import argparse,traceback


logging.basicConfig(format='%(levelname)s - %(asctime)s - %(message)s',datefmt='%d-%b-%y %H:%M:%S',level=logging.INFO)
LOGGER = logging.getLogger()
docdb = boto3.client('docdb')

#Function to get  instance count  with status - available, failed and pending   
def getInstanceStatus(cluster_id):
    istatus={"num_instances":-1}
    num_available = 0
    num_pending = 0
    num_failed = 0
    r = docdb.describe_db_instances(Filters=[{'Name':'db-cluster-id','Values': [cluster_id]}])
    instances = r['DBInstances']
    for i in instances:
        instance_id = i['DBInstanceIdentifier']
        instance_status = i['DBInstanceStatus']
        if instance_status == 'available':
            num_available = num_available + 1
        if instance_status in ['creating', 'deleting', 'starting', 'stopping']:
            num_pending = num_pending + 1
        if instance_status == 'failed':
                num_failed = num_failed + 1
    istatus["num_instances"]=len(instances)
    istatus["num_available"]=num_available
    istatus["num_pending"]=num_pending
    istatus["num_failed"]=num_failed
    return istatus

#Function to get cluster health 
def getClusterHealth(cluster_id):
    r = docdb.describe_db_clusters( DBClusterIdentifier=cluster_id)
    cluster_info = r['DBClusters'][0]
    istatus=getInstanceStatus(cluster_id)
    if cluster_info['Status'] == 'available' and istatus["num_available"]==istatus["num_instances"] :
        return True
    return False


#Function to get cluster instances and role 
def getClusterInstances(cluster_id):
    r = docdb.describe_db_clusters( DBClusterIdentifier=cluster_id)
    existing_instances = {}
    cluster_info = r['DBClusters'][0]
    if cluster_info['Status'] == 'available':
       for member in cluster_info['DBClusterMembers']:
            member_id = member['DBInstanceIdentifier']
            if member['IsClusterWriter']==True:
                existing_instances[member_id]='WRITER'
            else:
                existing_instances[member_id]='READER'
    return existing_instances

#Function to get writer instance for a given cluster id 
def getWriterInstance(cluster_id):
    instances=getClusterInstances(cluster_id=cluster_id)
    if len(instances)==0:
        raise RuntimeError("Not able to retrive primary instance") 
    reversed_dict = {}
    for key, value in instances.items():
        reversed_dict.setdefault(value, [])
        reversed_dict[value].append(key)
    return reversed_dict["WRITER"][0]
    


#Function to add the number of instances with size on a given cluster id     
def addInstances(cluster_id,desired_size,count):
    ninstances=[]
    for idx in range(count):
        instance_iden=cluster_id + '-' + str(idx) + '-' + str(int(time.time()))
        docdb.create_db_instance(DBInstanceIdentifier=instance_iden,DBInstanceClass=desired_size,Engine="docdb",DBClusterIdentifier=cluster_id)
        ninstances.append(instance_iden)
    return ninstances
        
#Function to delete the instances from instancelist 
def deleteInstances(instanceIdList):
    for instance in instanceIdList:
        docdb.delete_db_instance(DBInstanceIdentifier=instance)

#Function to perfrom failover using failover target         
def performFailover(cluster_id,failover_target):
    docdb.failover_db_cluster(DBClusterIdentifier=cluster_id,TargetDBInstanceIdentifier=failover_target)
    
#Function to check existing  instance class  
def checkExistingInstanceClass(cluster_id,itarget):
    r = docdb.describe_db_instances(Filters=[{'Name':'db-cluster-id','Values': [cluster_id]}])
    instances = r['DBInstances']
    iclist=[]
    for i in instances:
        iclist.append(i['DBInstanceClass'])
    if itarget in iclist:
        return True
    else:
        return False

#DocDB instance available waiter to check isntance status 
def docdbDBInstanceAvailableWaiter(cluster_id):
    waiter = docdb.get_waiter('db_instance_available')
    waiter.wait(Filters=[{ 'Name': 'db-cluster-id','Values': [cluster_id]}])


def main():
    
    parser = argparse.ArgumentParser(description='Amazon DocumentDB Cluster Scale up/down Tool.')
    parser.add_argument('--cluster-id',
                        required=True,
                        help='Amazon DocumentDB Cluster Identifer')
    
    parser.add_argument('--target-instance-type',
                        required=True,
                        type=str,
                        help='target instance type to perform scale up/down operation on given cluster id')

                        
    parser.add_argument('--ignore-instance-check',
                       required=False,
                       action='store_false',
                       help='ignore check for existing instances with target instance type (Optional)')
    
    args = parser.parse_args()

    cluster_id=args.cluster_id
    itarget=args.target_instance_type
    target_instance_check=args.ignore_instance_check
    valid_instance_classes=["db.r6g.large","db.r6g.xlarge","db.r6g.2xlarge","db.r6g.4xlarge","db.r6g.8xlarge","db.r6g.12xlarge","db.r6g.16xlarge","db.r5.large","db.r5.xlarge","db.r5.2xlarge","db.r5.4xlarge","db.r5.8xlarge","db.r5.12xlarge","db.r5.16xlarge","db.r5.24xlarge","db.t4g.medium","db.t3.medium"]

    #checking if the target instance class is valid.    
    if itarget not in valid_instance_classes:
        LOGGER.error("Target instance type "+ itarget +" is invalid. Exiting..")
        sys.exit(1)
    
    # Check for for cluster id and cluster health
    try:
        clusterHealth=getClusterHealth(cluster_id=cluster_id)
    except Exception as e :
        LOGGER.error(str(e))
        LOGGER.error("Please check the cluster id and try again. Exiting..")
        sys.exit(1)

    if not clusterHealth:
        LOGGER.error("Cluster is not healthy. Please make sure that cluster is in healthy state before running the tool. Exiting..")
        sys.exit(1)
    
    if target_instance_check and checkExistingInstanceClass(cluster_id=cluster_id,itarget=itarget):
        LOGGER.error("Cluster already has one of the instance with target instance type. If you want to still continue, please run with --ignore-instance-check. Exiting..")
        sys.exit(1)

    
    num_instances=getInstanceStatus(cluster_id)["num_instances"]
    oinstances=list((getClusterInstances(cluster_id)).keys())
    
    if num_instances > 8:
        LOGGER.error("Number of instances can not be more than 8 for this tool.")
        sys.exit(1)
    
    
    LOGGER.info("Target  instance type " + itarget)
    LOGGER.info("Number of instances to add  "+ str(len(oinstances))+", adding instances")
    ## Add instances
    try:
        ninstances=addInstances(cluster_id=cluster_id,desired_size=itarget,count=num_instances)
    except Exception as e :
        LOGGER.error(str(e))
        LOGGER.error("There is issue in adding instances,please fix the above exception and try again. Exiting..")
        sys.exit(1)

    LOGGER.info("waiting for new instances to become available, it can take up to 15 mins" )
    
    try:
        docdbDBInstanceAvailableWaiter(cluster_id)
    except Exception as e :
        LOGGER.error(str(e))
        LOGGER.error("New instances are not healthy after 15 mins. Exiting..")
        sys.exit(1)
    

    #Get failover target and current writer
    failover_target=ninstances[0]
    current_writer=getWriterInstance(cluster_id=cluster_id)


    LOGGER.info("Failover target " + failover_target)
    
    ## Perform failover 
    LOGGER.info("performing failover")
    try:
        performFailover(cluster_id=cluster_id,failover_target=failover_target)
        time.sleep(30)
    except Exception as e :
        LOGGER.error(str(e))
        LOGGER.error("There is issue with failover, please check the cluster health. Exiting..")
        sys.exit(1)
    count=0
    LOGGER.info("checking failover status")
    for count in range(10):
        try:
            nwriter=getWriterInstance(cluster_id=cluster_id)
        except Exception as e :
            LOGGER.warning(str(e))
            LOGGER.info("retrying to retrive new primary instance in 30 secs")
            count=count+1
            time.sleep(30)
            continue  
        if  nwriter in ninstances and current_writer!=nwriter:
            LOGGER.info("failover completed, new primary is " + nwriter)
            break
        LOGGER.info("sleeping for 30 secs to check failover status")
        count=count+1
        time.sleep(30)

    ## Delete  old instances 
    LOGGER.info("deleting old instances")
    try:
        deleteInstances(oinstances)
    except Exception as e :
        LOGGER.error(str(e))
        LOGGER.erbrror("There is issue with instance deletion, please check the cluster health. Exiting..")
        sys.exit(1)

    LOGGER.info("scaling tool execution finished.")

if __name__ == "__main__":
    main()
