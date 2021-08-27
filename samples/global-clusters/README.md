# Global Clusters Failover

Amazon DocumentDB Global Clusters allows you to promote secondary cluster(s) in a different AWS region to a primary cluster, during regional failures.The recomended steps to promote a secondary cluster are 

- Step 1: Stop Application from writing to primary
- Step 2: Identify secondary to promote based on latency for end users 
- Step 3: Remove and promote identified secondary to primary 
- Step 4: Delete old primary and other secondaries
- Step 5: Point application to new primary (standalone)

This script automates steps 3 and 4 by using AWS CLI. To install AWS CLI which is a pre-requisite to run this script, follow the instructions [here](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)

The script takes 3 parameters as input. 

- -g --> Global cluster identifer
- -r --> Secondary cluster identifer
- -d --> Indicator to delete global cluster after secondary cluster promotion is completed (Y/N). 


To run the script

- Clone the repo
- cd to the downloaded location
- Make the script executable ```chmod +x FailoverGlobalClusters.sh ```
- Use the below instructions to invoke the script
```
sh FailoverGlobalClusters.sh -g <'Global Cluster Identfier'> -r <'secondary cluster to promote'> -d <'Indicator to delete global cluster'>;

```

## Sample Input
```
sh FailoverGlobalClusters.sh -g 'globalClusterDemo' -r 'ohioCluster' -d 'N';
```

## Sample Output

```
Promoting secondary cluster *** virginiacluster *** to a standalone cluster.
Waiting for cluster promotion to complete...
Waiting for cluster promotion to complete...
Waiting for cluster promotion to complete...
Waiting for cluster promotion to complete...
Waiting for cluster promotion to complete...
Waiting for cluster promotion to complete...
Waiting for cluster promotion to complete...
Waiting for cluster promotion to complete...
Waiting for cluster promotion to complete...
Waiting for cluster promotion to complete...
Waiting for cluster promotion to complete...
Waiting for cluster promotion to complete...
Cluster promotion process completed.
********* SUCCESS : Secondary cluster virginiacluster  has been promoted to standalone primary. *********
``` 
```
sh FailoverGlobalClusters.sh -g 'globalClusterDemo' -r 'ohioCluster' -d 'Y';  

```
## Sample Output

```
Are you sure you want to delete the global cluster [Y/N]?Y
Promoting secondary cluster *** oregoncluster *** to a standalone cluster.
Waiting for cluster promotion to complete...
Waiting for cluster promotion to complete...
Waiting for cluster promotion to complete...
Waiting for cluster promotion to complete...
Waiting for cluster promotion to complete...
Waiting for cluster promotion to complete...
Waiting for cluster promotion to complete...
Waiting for cluster promotion to complete...
Waiting for cluster promotion to complete...
Cluster promotion process completed.
Deleting global cluster... globalClusterDemo
********* SUCCESS : Secondary cluster oregoncluster  has been promoted to standalone primary and global cluster globalClusterDemo  has been deleted. *********
```
