# Amazon DocumentDB Cluster Scale Up/Down Tool

The cluster scale up/down tool scales Amazon DocumentDB Cluster with target instance type. 

Tool performs scaling operations in three simple steps as below and it does not change the number of instances.
 - Add same number of new instances with target instance type.
 - Perform the failover from current instance to newly create instance.
 - Remove old instances.

# Requirements
 - Python 3.7+
 - pymongo Python package - tested versions
   - pymongo 4.4+
   - If not installed - "$ pip3 install pymongo"
 - AWS SDK for Python - tested versions 
   - boto3 1.28+
   - If not installed - "$ pip3 install boto3"


## Using the Scale Up/Down Tool
`python3 scaleupdown.py  --cluster-id <cluster-id> --target-instance-type <target-instance-type>  `
- Run on any AWS Cloud9 or Bastion host(Jump host) where aws cli is configured.
- Provide a valid cluster id - Mandatory
- Pass a valid instance type - Mandatory
- Ignore the check for existing instances for target instance type using --ignore-instance-check (Optional)

## License
This tool is licensed under the Apache 2.0 License. 
