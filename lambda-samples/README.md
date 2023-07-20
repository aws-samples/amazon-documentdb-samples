# Lambda with Amazon DocumentDB

Follow these steps in order to execute a Lambda function that interacts with an Amazon DocumentDB cluster

### 1. Create a Lambda layer
A Lambda layer is a package of custom code or libraries that can be added to your Lambda functions. It helps you avoid duplicating code and allows you to manage and share code and libraries across multiple Lambda functions.
For example, for a Lambda function written in Python, you'll need external libraries such as Pymongo to connect to and query data from an Amazon DocumentDB cluster. Instead of building the dependencies in each function, one layer can be shared by all the Lambda functions that require this dependency.

To create a layer that contains the Pymongo library (for Python), or the MongoDB package (for NodeJS), along with the CA certificate, see the [Lambda layers repository for Amazon DocumentDB](https://github.com/aws-samples/amazon-documentdb-samples/tree/master/lambda-layers). Additionally, you can review the [Lambda Documentation](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html) for creating and configuring a layer.

### 2. Create a function execution role for Lambda
A role allows you to define the necessary permissions and access rights that the Lambda function requires to interact with other AWS services and resources. 
 - Open the Identity and Access Management (IAM) console at https://console.aws.amazon.com/iamv2/
 - Create a policy that allows read access to `AWS Secrets Manager`. From the Access Management left-hand menu, choose Policies and then "Create Policy". Choose JSON and add the definition below. In the next step give the policy the name `AWSSecretsManagerReadAccess` and create it. 

**Note**: This policy allows read access to all secrets, modify accordingly to permit access only to required secrets.

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:ListSecrets",
                "secretsmanager:GetSecretValue"
            ],
            "Resource": [
                "*"
            ]
        }
    ]
}
```

 - Create a role for Lambda. From the Access Management left-hand menu, choose Roles and then "Create Role".
 - Select "AWS service" as the trusted entity, choose "Lambda" as the service, and proceed to "Next: Permissions."
 - Search for and select the `AWSLambdaVPCAccessExecutionRole` and `AWSSecretsManagerReadAccess` policies.
 - Proceed to the next steps, review the role details and give it a meaningful name, for example `LambdaDocDBRole`.
 - Create the role.

### 3. Create a Security Group for Lambda
Create a security group that will be attached to the Lambda function.
- Open the Amazon VPC console at https://console.aws.amazon.com/vpc/ and in the navigation pane choose `Security groups`, then `Create security group`.
- Enter a name and description for the security group. For the VPC, choose the VPC where the Amazon DocumentDB cluster is deployed.
- Leave the defaults in place, no Inbound rules and Allow all traffic for Outbound rules.
- Choose Create security group.

### 4. Update the security group attached with the Amazon DocumentDB cluster
To allow access from the Lambda function, you need to update the security group attached with the Amazon DocumentDB cluster and allow access from the security group created in the previous step.

- Open the Amazon VPC console at https://console.aws.amazon.com/vpc/ and in the navigation pane choose `Security groups`, then select the security group attached with the Amazon DocumentDB cluster.
- Edit inbound rules and add a new rule, Type Custom TCP, for port range enter 27017 (or the port configured for Amazon DocumentDB), source Custom and select the security group created at step 3.


### 5. Create a VPC Endpoint for Secrets Manager
To retrieve the credentials to the database securely, it is recommended to establish a private connection between the VPC used by Lambda and Secrets Manager, by creating an interface VPC endpoint.
- Follow the steps to [Create an interface endpoint](https://docs.aws.amazon.com/vpc/latest/privatelink/create-interface-endpoint.html#create-interface-endpoint-aws). For AWS Service choose `com.amazonaws.<region name>.secretsmanager` and select the VPC used by Lambda and Amazon DocumentDB.
- You'll attach a security group with the VPC endpoint. It's important to update the security group inbound rules, add a rule to allow TCP traffic on port 443 (https) with source the security group attached with the Lambda function. This will allow the Lambda function to connect to Secrets Manager and retrieve the credentials.

### 6. Create the Lambda function

- Open the Lambda console at https://console.aws.amazon.com/lambda/home#/functions and choose `Create function`.
- Leave `Author from scratch` selected, and in Basic information enter a name for the function, for example `LambdaFunctionWithDocDB`.
- Select your prefered runtime, for example Python 3.9.
- In the `Change default execution role` drop down select `Use an existing role` and choose the role created at step 2, `LambdaDocDBRole`.
- In `Advanced Settings` select `Enable VPC` and choose the VPC where Amazon DocumentDB cluster is deployed, select the same `Subnets` as DocumentDB and for the Security group choose the one created at step 3.
- Choose `Create function`.


Finally, explore the [samples](https://github.com/aws-samples/amazon-documentdb-samples/tree/master/lambda-samples/samples) to experiment with several Lambda functions.
