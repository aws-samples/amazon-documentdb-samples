# Amazon DocumentDB Cluster Scale Up/Down Tool

The cluster scale up/down tool scales Amazon DocumentDB Cluster with target instance type. 

Tool performs scaling operations in three simple steps as below and it does not change the number of instances.
 - Add same number of new instances with target instance type.
 - Perform the failover from current instance to newly create instance.
 - Remove old instances.

# Requirements
 - Python 3.8+
 - pymongo Python package - tested versions
   - pymongo 4.4+
   - If not installed - "$ pip3 install pymongo"
 - AWS SDK for Pythoni(Boto3) - tested versions 
   - boto3 1.28+
   - If not installed - "$ pip3 install boto3"
 - Configure Boto3 credentials
   - Configure AWS IAM role to access Amazon DocumentDB and assign to Amazon EC2 instance. 
   - There are multiple ways to configure Boto3 credentials. You can refer here : https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
   - Recommnedation is to use AWS IAM role if you are running tool from Amazon EC2.


## Using the Scale Up/Down Tool
`python3 scaleupdown.py  --cluster-id <cluster-id> --target-instance-type <target-instance-type>  `
- Provide a valid cluster id - Mandatory
- Pass a valid instance type - Mandatory
- Ignore the check for existing instances for target instance type using --ignore-instance-check (Optional)

## Sample command
```python
python3 scaleupdown.py --cluster-id source-docdb-3-6-cluster --target-instance-type db.r5.medium
```
## License
This tool is licensed under the Apache 2.0 License. 
