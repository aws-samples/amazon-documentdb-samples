# Morphia – Java ODM for Amazon DocumentDB 

## Introduction

This is a sample project to demonstrate integration between Morphia ODM library and Amazon DocumentDB. 

Morphia is an Object-Document Mapping (ODM) library built as a wrapper around Java drivers. An ODM is a programming technique used to facilitate the interaction between object-oriented programming languages (like Java) and document-oriented databases (like DocumentDB and MongoDB), which store data in a flexible, schema-less manner. Morphia provides a way to map Java objects to DocumentDB documents and vice versa. This means that you can work with DocumentDB using Java objects and their corresponding methods, rather than directly dealing with low-level JSON queries and documents.

In this sample project, we explore the basics of using a Morphia ODM library. In the process, you also learn how to seamless integrate with Amazon DocumentDB.

## Requirements

* An AWS account
* An Amazon DocumentDB cluster – You can integrate your Amazon DocumentDB cluster with Java application using Morphia ODM libraries. If you don’t already have an Amazon DocumentDB cluster, see Getting Started with [Amazon DocumentDB (with MongoDB compatibility)](https://docs.aws.amazon.com/documentdb/latest/developerguide/get-started-guide.html) to create a new cluster.
* An integrated development environment (IDE) – You can use  [AWS Cloud9](https://aws.amazon.com/cloud9/) for demonstration, which is a cloud-based IDE that lets you write, run, and debug your code with just a browser. It includes a code editor, debugger, and terminal. [Enable Enhanced support](https://docs.aws.amazon.com/cloud9/latest/user-guide/enhanced-java.html)for Java development to improve your development experience when working with Java.
* Java 17 – Install or upgrade Java in AWS Cloud9. For more information, see [Amazon Corretto 17 Installation Instructions.](https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/amazon-linux-install.html)
*  Maven - [Set up with Maven](https://docs.aws.amazon.com/cloud9/latest/user-guide/sample-java.html#sample-java-sdk-maven) to install Maven in AWS Cloud9

You may incur costs in your account related to Amazon DocumentDB and AWS Cloud9 resources. You can use the [AWS Pricing Calculator](https://calculator.aws/#/) to estimate the cost.


## Installation Instructions

1. On command prompt/terminal/Cloud9 environment, Create a new directory, navigate to the directory

2. Clone the GIT repository with the following command

```bash
 git clone https://github.com/aws-samples/amazon-documentdb-samples.git
```

## Update Configuration 

To connect to Amazon DocumentDB cluster, you specify the connection URI string in the App.java file located in the `docdb-morphia-starter/src/main/java/com/example/morphia/docdb` folder.

Update Amazon DocumentDB connection URI for constant `docdb_uri` in  App.java file.  Make sure your copied connection string is in below format. Replace `<user name>`, `<password>` and `<cluster end point>` with your cluster specific details. 

```bash  
mongodb://<user name>:<password>@<cluster end point>: 27017/?ssl=true&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false
``` 


## Connecting with TLS Enabled
For connecting to a TLS-enabled Amazon DocumentDB cluster from a java based application, your program must use the AWS-provided certificate authority (CA) file to validate the connection. To use the Amazon RDS CA certificate, do the following:
1.  Create a temporary certs folder under tmp folder.  You can create the folder for storing the certificates based on your organization security policies. For this post you are creating certs folder under tmp

```bash 
mkdir /tmp/certs/ 
```

2.  Create a trust store with the CA certificate contained in the file by performing the following commands. 

The following is a sample shell script that imports the certificate bundle into a trust store on a Linux operating system. For other options , see Connecting with TLS Enabled.

```bash 
mydir=/tmp/certs
truststore=${mydir}/rds-truststore.jks
storepassword=changeit

curl -sS "https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem" > ${mydir}/global-bundle.pem
awk 'split_after == 1 {n++;split_after=0} /-----END CERTIFICATE-----/ {split_after=1}{print > "rds-ca-" n ".pem"}' < ${mydir}/global-bundle.pem

for CERT in rds-ca-*; do
  alias=$(openssl x509 -noout -text -in $CERT | perl -ne 'next unless /Subject:/; s/.*(CN=|CN = )//; print')
  echo "Importing $alias"
  keytool -import -file ${CERT} -alias "${alias}" -storepass ${storepassword} -keystore ${truststore} -noprompt
  rm $CERT
done

rm ${mydir}/global-bundle.pem

echo "Trust store content is: "

keytool -list -v -keystore "$truststore" -storepass ${storepassword} | grep Alias | cut -d " " -f3- | while read alias 
do
   expiry=`keytool -list -v -keystore "$truststore" -storepass ${storepassword} -alias "${alias}" | grep Valid | perl -ne 'if(/until: (.*?)\n/) { print "$1\n"; }'`
   echo " Certificate ${alias} expires in '$expiry'" 
done

```

## Run and Test

Run your Java application with following Maven command from `docdb-morphia-starter/` folder: 

```bash
mvn compile exec:java -Dexec.mainClass="com.example.morphia.docdb.App" -Dexec.cleanupDaemonThreads=false 
```



