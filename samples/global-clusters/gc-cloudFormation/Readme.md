# Amazon DocumentDB Global Cluster CloudFormation Templates

This repository contains AWS CloudFormation templates to launch and manage Amazon DocumentDB Global clusters.

Amazon DocumentDB Global Clusters allow you to create a single, unified database that spans multiple AWS Regions. This setup provides multiple benefits:

- Low-latency global reads
- Disaster recovery from region-wide outages
- Seamless scaling across geographical locations

## Templates

This repository includes two key CloudFormation templates:

1. `create_docdb_globalcluster.yaml:` This template creates the foundation of your global database architecture. It sets up a Global Cluster and deploys a primary Amazon DocumentDB cluster with three instances in the region.

2. `addRegion_globalCluster.yaml:` Use this template to expand your global footprint. It adds a secondary region to your existing Global Cluster, allowing for global read scaling and improved disaster recovery.

## Prerequisites

Before you begin, ensure you have:

- An AWS account with appropriate permissions for creating DocumentDB resources.
- VPC networking already set up in each region where you plan to deploy DocumentDB clusters. This should include:
  - A VPC with appropriate subnets
  - A security group configured for Amazon DocumentDB access
  - A DB subnet group

## Implementation Guide

### Step 1: Deploy the Primary Global Cluster

1. Clone the repository 
2. Navigate to the AWS CloudFormation console in your primary region.
3. Create a new stack using the `create_docdb_globalcluster.yaml` template.
4. Fill in the required parameters
    - `Stack name:` A unique name to identify your CloudFormation stack in the region.
    - `Amazon DocumentDB Global Cluster Identifier:` A unique name for your global DocumentDB cluster. This identifier will be used across all regions. It must start with a letter and can only contain alphanumeric characters.
    - `Primary Region Cluster Identifier:` A unique name for the Amazon DocumentDB cluster in your primary region. It must start with a letter and can only contain alphanumeric characters.
    - `Amazon DocumentDB Instance Class:` Select the Amazon DocumentDB instance class for Primary region cluster from the list.
    - `Database Subnet Group:` The name of an existing DB subnet group in primary region VPC. DocumentDB requries subnet group consisting of minimum of 2 subnets.
    - `Security Group`:  Choose from the list of existing VPC security groups. This security group/s will control network access to your Amazon DocumentDB cluster in the primary region.
    - `Amazon DocumentDB Username:` The name of the Admin user for your Amazon DocumentDB cluster. This user will have full administrative privileges. Choose a unique username that's not a reserved word in DocumentDB.
    - `Amazon DocumentDB Password:` A strong password for the master user account. It must be at least 8 characters long and can contain letters, numbers, and symbols.  Avoid special characters like '/', '@', or '"' .
5. Review and create the stack.

This process will set up your Global Cluster and deploy the primary DocumentDB cluster with three instances.

### Step 2: Add Secondary Regions

1. Choose a secondary region and navigate to its CloudFormation console.
2. Create a new stack using the `addRegion_globalCluster.yaml` template.
3. Fill in the required parameters:
   - `Stack name:` A unique name to identify your CloudFormation stack in the region.
   - `Global Cluster Identifier:` Identifier for exisiting Global cluster (must exactly match)
   - `Secondary Cluster Identifier:` A unique name for the Amazon DocumentDB cluster in your secondary region. It must start with a letter and can only contain alphanumeric characters.
   - `Amazon DocumentDB Instance Class`: Select the Amazon DocumentDB instance class for Primary region cluster from the list.
   - `Database Subnet Group Name:`  The name of an existing DB subnet group in the secondary region VPC
   - `Security Group:` Choose from the list of existing VPC security groups. This security group/s will control network access to your Amazon DocumentDB cluster in the secondary region
4. Review and create the stack.

This process will add secondary region for Amazon DocumentDB cluster with one instance.

Repeat this step for each additional region you wish to add to your Global Cluster.

## Contributing

Contributions to improve these templates are welcome. See CONTRIBUTING file.

## License

This project is licensed under the MIT License. See the LICENSE file.
