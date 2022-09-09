# DotNet / CSharp Starter project for Amazon DocumentDB

## Introduction
Setting up development environment for a new database may require going through countless tutorials and documentation pages. This is an example DotNet project that sets up development environment locally to work with Amazon DocumentDB. Project creates all required infrastructure, networking and resources to get started on your first WebAPI project using Csharp. This example has been been modified from [TodoApis Tutorial](https://docs.microsoft.com/en-us/aspnet/core/tutorials/first-web-api?view=aspnetcore-6.0&tabs=visual-studio) from Microsoft. Example uses ssh tunnel to work locally with Amazon DocumentDB and also uses AWS Secrets Manager to store database credentials. Follow the steps below to finish the installation. 


## Feature List at High Level
1. Orchestration through cloudformation template for VPC, Gateways, Amazon DocumentDB and EC2 jump server. 
2. DotNet Sample Web API project.
3. SecretsManager Integration for secured access to database credentials. 
4. EC2 Jump server to connect to database as Amazon DocumentDB is a VPC only service. 

![Architecture](./images/dotnet-docdb-starter-project.png)

## Requirements 
1. DotNet Core 6.0+ Installed
2. [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) 2.4+  You must have run `aws configure` to set up your terminal for the AWS account and region of your choice.
3. Make command line tools.  MacOs(https://formulae.brew.sh/formula/make), Windows (https://linuxhint.com/install-use-make-windows/) 
4. Amazon DocumentDB [Mongo shell commands](https://docs.aws.amazon.com/documentdb/latest/developerguide/get-started-guide.html#cloud9-mongoshell). 


## Getting Started
Follow the following steps to setup environment locally


### Step 1 : Clone DotNet Starter project locally
Clone this project using following command: 

```
git clone https://github.com/aws-samples/amazon-documentdb-samples/tree/master/samples/docdb-dotnet-starter
cd docdb-dotnet-starter
```

### Step 2 : Create EC2 Key pair 
Use the following commands to create key pair and save that to the project. If you decide to change the key name then note it down. We will need to make changes to commands accordingly. 
```
mkdir keys
aws ec2 create-key-pair --key-name ec2-keypair --query 'KeyMaterial' --output text > keys/ec2-keypair.pem
chmod 400 keys/ec2-keypair.pem
```

### Step 3 : Deploy cloudformation template to setup infrastructure

```
make infra
```
Above will take about 15 mins to setup all the resources and permissions. You can check the progress of the CloudFormation [here](https://console.aws.amazon.com/cloudformation/home) and once complete you will see `'CREATE_COMPLETE'` message on CloudFormation Dashboard. 

### Step 4 : Start SSH Tunnel 
```
make tunnel
```
### Step 5 : Build your project and Webapplication 
This command may be needed to run in a separate terminal/command prompt. 
```
dotnet build
dotnet run
```

### Step 6 : Verity Web Apis 
Commands at Step 4 shows the address and port where Web Apis are running. Open your favorite browser and start the following page. 
```
https://localhost:5001/api/Locations
```
This should return empty results right now as there is no data loaded to DocumentDB Yet. Lets take care of that in following steps. 

### Step 7 : Load data to Amazon DocumentDB
This uses Restaurants.json file that comes with this project in the `data` directory. Use the following command to load to Amazon DocumentDB. 
```
mongoimport --username docdb --password docdb123 --file=data/restaurant.json --db=restaurants --collection=locations --writeConcern "{w:0}"
```

### Step 8 : Verify Data
Go back to your browser and refresh, you should now see list of restaurant locations coming back as a result set. 
```
https://localhost:5001/api/Locations
```

### Verify Data in Amazon DocumentDB(Optional)
You can also connect to Amazon DocumentDB directly to verify data using mongo shell. Use following commands to verify:
```
mongosh --username docdb --password docdb123
```