#!/bin/sh
while getopts g:r:d: flag
do
    case "${flag}" in
        g) globalClusterIdentifer=${OPTARG};;
        r) regionalClusterIdentiferInput=${OPTARG};;
        d) deleteGlobalCluster=${OPTARG};;
    esac
done

if [ -z "$globalClusterIdentifer" ]; 
then
echo "Please provide a value for Global Cluster Indentifier by using -g argument"
exit 1
fi

if [ -z "$regionalClusterIdentiferInput" ]; 
then
echo "Please provide a value for regional Cluster Indentifier to promote to standalone by using -r argument"
exit 1
fi

if [ -z "$deleteGlobalCluster" ]; 
then
echo "Please provide a value to delete cluster by using -d argument"
exit 1
fi

if [[ $deleteGlobalCluster = 'Y' ]] 
then
while true; do
    read -r -p "Are you sure you want to delete the global cluster [Y/N]?" _response
    case "$_response" in
      [Yy][Ee][Ss]|[Yy]) # Yes or Y (case-insensitive).
        break;
        ;;
      [Nn][Oo]|[Nn])  # No or N.
        exit 1
        ;;
      *) # Anything else (including a blank) is invalid.
        ;;
    esac
done
fi

# This function will catch error for any CLI command that modifies the cluster (deletion or promotion) and displayes the error to the user
function errorCheck
{
	if [[ $1 =~ "An error occurred" ]]; 
	then
		echo "ERROR OCCURRED WHILE PROCESSING: ---> "$1
		echo "PROCESSING WILL STOP!"
		exit 1
	fi
}

# This function will remove secondary cluster from a given global cluster and promote it to standalone cluster
function removeFromGlobalCluster
{
	
	region=$(echo $1 | cut -d ':' -f 4)
	promotedCluster=$(aws docdb remove-from-global-cluster --region $region --db-cluster-identifier $1 --global-cluster-identifier $2 2>&1)
	errorCheck "$promotedCluster"
}

# This function will remove individual instances from a cluster and eventually delete the cluster. 
function deleteCluster
{
region=$(echo $1 | cut -d ':' -f 4)
clusterInstances=$(aws docdb describe-db-clusters --region $region --db-cluster-identifier $1 --output text --query 'DBClusters[0].DBClusterMembers[].DBInstanceIdentifier')
clusterInstances=(${clusterInstances//'\n'/ })
for eachInstance in ${clusterInstances[@]};do
	#Delete instances
	deletedInstance=$(aws docdb delete-db-instance --region $region --db-instance-identifier $eachInstance 2>&1)
	errorCheck "$deletedInstance"
done
# Disable deletion protection
disableDeleteProtection=$(aws docdb modify-db-cluster --region $region --db-cluster-identifier $1 --no-deletion-protection --apply-immediately) 
# Delete cluster
deletedCluster=$(aws docdb delete-db-cluster --region $region --db-cluster-identifier $1 --skip-final-snapshot 2>&1) 
errorCheck "$deletedCluster"  
}

# This function will check the promotion status of the secondary cluster in a loop with a 10 sec delay and will exit the loop when all secondaries are promoted
function waitForPromotionToComplete
{
remainingsecondaryClusters=$(aws docdb describe-global-clusters --global-cluster-identifier $1 --output text --query 'GlobalClusters[0].GlobalClusterMembers[?IsWriter== `true`].Readers[]')
remainingsecondaryClusters=(${remainingsecondaryClusters//'\n'/ })
while [ ${#remainingsecondaryClusters[@]} > 0 ]
do
	sleep 10s
	remainingsecondaryClusters=$(aws docdb describe-global-clusters --global-cluster-identifier $1 --output text --query 'GlobalClusters[0].GlobalClusterMembers[?IsWriter== `true`].Readers[]')
	remainingsecondaryClusters=(${remainingsecondaryClusters//'\n'/ })
	echo "Waiting for cluster promotion to complete..."
	
	# The below code is to check if the secondary cluster provided as input has been deleted. This is to be used when global cluster delete indicator is 'N'
	clusterPromotionInprogress=false
	for eachCluster in ${remainingsecondaryClusters[@]};do
	secondaryClusterIdentifer=$(echo $eachCluster | cut -d ':' -f 7)
	if [[ $secondaryClusterIdentifer = $2  ]]; then
		clusterPromotionInprogress=true
		break
	fi
	done

if [[ ${#remainingsecondaryClusters[@]} = 0 ]]; then
	echo "Cluster promotion process completed."
	break
elif [[ $clusterPromotionInprogress = false ]] && [[ $deleteGlobalCluster = 'N' ]]; then 
	echo "Cluster promotion process completed."
	break
fi
done
}

#Execution begins here...
#Retrieve all secondary clusters for the global cluster and convert result to array for further processing
secondaryClusters=$(aws docdb describe-global-clusters --global-cluster-identifier $globalClusterIdentifer --output text --query 'GlobalClusters[0].GlobalClusterMembers[?IsWriter== `true`].Readers[]')
secondaryClusters=(${secondaryClusters//'\n'/ })
#Exit if no secondary clusters are available
if [[ ${#secondaryClusters[@]} = 0 ]]; then
	echo "No secondary clusters found for provided cluster "$globalClusterIdentifer ".Please check provided input."
	exit 1
fi
# To minimize failover time, identify and promote the regional cluster provided as input. 
promotedRegionalCluster=false
for eachSecondaryCluster in ${secondaryClusters[@]};do
	regionalClusterIdentifer=$(echo $eachSecondaryCluster | cut -d ':' -f 7)
		if [[ $regionalClusterIdentifer = $regionalClusterIdentiferInput ]] 
		then
			echo "Promoting secondary cluster *** "$regionalClusterIdentifer "*** to a standalone cluster."
			removeFromGlobalCluster $eachSecondaryCluster $globalClusterIdentifer
			promotedRegionalCluster=true
			break;
		fi
done
if [[ $promotedRegionalCluster = false ]]; 
then
	echo "No matching secondary cluster found for *** "$regionalClusterIdentiferInput "***.Please check provided input."
	exit 1
fi

#Proceed to delete the global cluster as indicated by user via input
if [[ $deleteGlobalCluster = 'Y' ]] 
then
	# Remove and promote all clusters to standalone clusters
	for eachSecondaryCluster in ${secondaryClusters[@]};do
		regionalClusterIdentifer=$(echo $eachSecondaryCluster | cut -d ':' -f 7)
			if [[ $regionalClusterIdentifer != $regionalClusterIdentiferInput ]]; 
			then
				removeFromGlobalCluster $eachSecondaryCluster $globalClusterIdentifer 
			fi
	done

# Wait until all standalone clusters are promoted
waitForPromotionToComplete $globalClusterIdentifer $regionalClusterIdentiferInput
echo "Deleting global cluster... "$globalClusterIdentifer
# Delete secondary clusters
for eachSecondaryCluster in ${secondaryClusters[@]};do
		regionalClusterIdentifer=$(echo $eachSecondaryCluster | cut -d ':' -f 7)
			if [[ $regionalClusterIdentifer != $regionalClusterIdentiferInput ]]; 
			then
				deleteCluster $eachSecondaryCluster
			fi
done

# delete primary cluster
primaryCluster=$(aws docdb describe-global-clusters --global-cluster-identifier $globalClusterIdentifer --output text --query 'GlobalClusters[0].GlobalClusterMembers[?IsWriter== `true`].DBClusterArn')
removeFromGlobalCluster $primaryCluster $globalClusterIdentifer
deleteCluster $primaryCluster

# delete global cluster
primaryRegion=$(echo $primaryCluster | cut -d ':' -f 4)
deletedGlobalCluster=$(aws docdb --region $primaryRegion delete-global-cluster --global-cluster-identifier $globalClusterIdentifer 2>&1)
errorCheck "$deletedGlobalCluster"
echo "********* SUCCESS : Secondary cluster "$regionalClusterIdentiferInput " has been promoted to standalone primary and global cluster "$globalClusterIdentifer " has been deleted. *********"
else 
	waitForPromotionToComplete $globalClusterIdentifer $regionalClusterIdentiferInput
	echo "********* SUCCESS : Secondary cluster "$regionalClusterIdentiferInput " has been promoted to standalone primary. *********"
fi