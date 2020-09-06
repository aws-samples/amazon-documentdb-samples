
## Amazon DocumentDB (with MongoDB compatibility) templates

This folder contains templates for deploying Amazon DocumentDB topologies. 

Amazon DocumentDB is secure by design:

- Amazon DocumentDB is VPC-only, meaning that, by default, when we you launch an Amazon DocumentDB cluster you will have strict network isolation and your cluster will not be accessible from the Internet.
- By default, Amazon DocumentDB encrypts all of your data in-transit with TLS and at-rest with KMS.
- By default, authentication is enabled on Amazon DocumentDB and it cannot be disabled. Amazon DocumentDB clusters launch with the most secure defaults and you can optionally choose to modify those defaults if you choose.
- Amazon DocumentDB allows you to encrypt your databases using keys you create and control through AWS Key Management Service (KMS). 

### Amazon DocumentDB baseline

Since Amazon DocumentDB is VPC-only and will not be accessible from the Internet, it is not the best approach to launch a cluster within the default VPC because all its subnets are public. Therefore, it is recommended to deploy a VPC with a more appropiate network topology for DocumentDB

This Cloudformation template deploys:  
- A VPC with 3 public and 3 private subnets. 
- An Amazon DocumentDB cluster with a master and 2 replicas spread in different availiability zones. 
- A Cloud9 environment that serves as a jumbbox for the Amazon DocumentDB cluster. 

Once the template is deployed, access the Cloud9 workspace. Open a terminal within the workspace and run the following commands:

´´´
echo -e "[mongodb-org-3.6] \nname=MongoDB Repository\nbaseurl=https://repo.mongodb.org/yum/amazon/2013.03/mongodb-org/3.6/x86_64/\ngpgcheck=1 \nenabled=1 \ngpgkey=https://www.mongodb.org/static/pgp/server-3.6.asc" | sudo tee /etc/yum.repos.d/mongodb-org-3.6.repo
sudo yum install -y mongodb-org-shell
wget https://s3.amazonaws.com/rds-downloads/rds-combined-ca-bundle.pem

´´´

To get the connection string, go the Amazon DocumentDB console. Then under Clusters, select the cluster you deployed. It will show detail information of you cluster, under the 'Connect' section you can copy the connnection string. Paste it in the workspace, include the cluster password and connect to your DocumentDB cluster. 

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

## Questions/feature requests?

Email questions to: documentdb-feature-request@amazon.com
