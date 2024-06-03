
# Steps to build a Docker image using Quarkus framework and Panache ORM library to connect to Amazon DocumentDB

## Introduction

In this sample we demonstrate

1. How to create a sample Java application using Quarkus framework that connects to Amazon DocumentDB
2. How to use Panache ORM library to interact with Amazon DocumentDB from the code
3. How to build a sample Docker image from the code
4. How to run a local container based on that image and test the endpoints

### What are Docker containers

A container is a standard unit of software that packages up code and all its dependencies so the application runs quickly and reliably from one computing environment to another. A [Docker container](https://www.Docker.com/resources/what-container/) image is a lightweight, standalone, executable package of software that includes everything needed to run an application: code, runtime, system tools, system libraries and settings.

To learn more about containerization and its benefits, please read [resource](https://aws.amazon.com/what-is/containerization/)

### What is Quarkus?

[Quarkus](https://quarkus.io/) was created to enable Java developers to create applications for a modern, cloud-native world. Quarkus is a Kubernetes-native Java framework.

### MongoDB with Panache
[MongoDB with Panache](https://quarkus.io/guides/mongodb-panache) provides active record style entities (and repositories) like you have in Hibernate ORM with Panache and focuses on making your entities trivial and fun to write in Quarkus.

It is built on top of the [MongoDB Client extension](https://quarkus.io/guides/mongodb).

## Prerequisites

To implement this solution, you must have the following prerequisites:
    
* An [Amazon EC2 Instance](https://aws.amazon.com/pm/ec2/) where you can test scripts to generate database connections. You can use an existing Amazon EC2 instance or [create a new one](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/EC2_GetStarted.html).  For this test, we have used a t2.large instance type created with [AMI](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AMIs.html) *Amazon Linux 2023 AMI 2023.4.20240401.1 x86_64 HVM kernel-6.1*.

* An Amazon DocumentDB cluster with at least two db.r6g.large instances. You can use an existing Amazon DocumentDB cluster or [create a new one](https://docs.aws.amazon.com/documentdb/latest/developerguide/db-cluster-create.html). This post assumes the default values for port (27017) and TLS (enabled) settings.

* A security group that enables you to connect to your Amazon DocumentDB cluster from your Amazon EC2 instance. You can use an existing security group or [create a new one](https://docs.aws.amazon.com/documentdb/latest/developerguide/get-started-guide.html#cloud9-security). You may also use the [Connect using Amazon EC2](https://docs.aws.amazon.com/documentdb/latest/developerguide/connect-ec2.html) feature to connect your Amazon DocumentDB cluster to your Amazon EC2 instance. 
* [Modify your EC2 instance](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/authorizing-access-to-an-instance.html) security group to allow SSH from your local IP.

## Setup environment in the  Amazon EC2 Instance

1. [SSH](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-to-linux-instance.html) into the EC2 instance
2. Install Java 17

```
    sudo yum install Java-17-amazon-corretto-devel
```

3. Check Java version

```
    java --version
```

The output should show jdk 17

```
    openjdk 17.0.10 2024-01-16 LTS
    OpenJDK Runtime Environment Corretto-17.0.10.8.1 (build 17.0.10+8-LTS)
    OpenJDK 64-Bit Server VM Corretto-17.0.10.8.1 (build 17.0.10+8-LTS, mixed mode, sharing)
```

4. Install and configure Docker to run with ec2-user

```
    sudo yum update -y
    sudo yum install -y docker
    sudo service docker start
    sudo usermod -a -G Docker ec2-user
    sudo reboot
```
	
Note : the EC2 instance will reboot after these steps

5. [SSH](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-to-linux-instance.html) into the EC2 instance
6. Install Quarkus framework

```
    curl -Ls https://sh.jbang.dev | bash -s - trust add https://repo1.maven.org/maven2/io/quarkus/quarkus-cli/
    curl -Ls https://sh.jbang.dev | bash -s - app install --fresh --force quarkus@quarkusio
    sudo reboot
```
Note : the EC2 instance will reboot after these steps

7. [SSH](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-to-linux-instance.html) into the EC2 instance

8. Check quarkus version

```
    quarkus --version
```

The output should show the current quarkus version

```
    3.9.2
```

9. Install git 

```
    sudo yum install git
```

## Prepare and Test Application Code

1. Download the code from repository

```
    git clone https://github.com/aws-samples/amazon-documentdb-samples.git
```

2. Make code executable 

```
    chmod -R 700 amazon-documentdb-samples/samples/docdb-Docker-quarkus-panache/documentdb-quarkus-quickstart/
```

3. Change directory

```
    cd amazon-documentdb-samples/samples/docdb-Docker-quarkus-panache/documentdb-quarkus-quickstart/
```

This Java code has two packages :

| Package              | Purpose                |
| :---------------- |  :-------------------   
|com.aws.documentdb.panache.entity|This provides the sample code for [using the active record pattern](https://quarkus.io/guides/mongodb-panache#solution-1-using-the-active-record-pattern)| 
|com.aws.documentdb.panache.repository|This provides the sample code for [using the repository pattern](https://quarkus.io/guides/mongodb-panache#solution-2-using-the-repository-pattern)| 

Both packages have the Person class which defines the structure of the document to be stored in collection "person"

```
    @MongoEntity(collection = "person")
    public class Person {			
```

4. Run script to load DocumetnDB TLS certificates to custom Java truststore for the Docker image

```
    ./files/docdbcerts.sh
```

5. Run script to load DocumetnDB TLS certificates to default Java truststore for the local build

```
    ./files/docdbcerts_local.sh
```

6. Change the property in file src/main/resources/application.properties
```
    quarkus.mongodb.connection-string = <documentdb_uri>>
    quarkus.mongodb.database = <<databse_name>>
```
7. Change the property in file src/test/resources/application.properties
```
    quarkus.mongodb.connection-string = <documentdb_uri>>
    quarkus.mongodb.database = <<databse_name>>
```
8. Run Quarkus test

```
    ./mvnw compile quarkus:dev -DJavax.net.ssl.trustStore=/tmp/certs/rds-truststore.jks -DJavax.net.ssl.trustStorePassword=password -Dquarkus.http.host=0.0.0.0
```

The output in the console would pause in the following screen

    __  ____  __  _____   ___  __ ____  ______ 
     --/ __ \/ / / / _ | / _ \/ //_/ / / / __/ 
     -/ /_/ / /_/ / __ |/ , _/ ,< / /_/ /\ \   
    --\___\_\____/_/ |_/_/|_/_/|_|\____/___/   
    2024-04-03 18:51:43,409 WARN  [org.mon.dri.uri] (Quarkus Main Thread) Connection string contains unsupported option 'tlscafile'.
    2024-04-03 18:51:43,519 INFO  [io.quarkus] (Quarkus Main Thread) documentdb-panache-quickstart 1.0.0-SNAPSHOT on JVM (powered by Quarkus 3.9.1) started in 2.295s. Listening on: http://localhost:8080
    2024-04-03 18:51:43,521 INFO  [io.quarkus] (Quarkus Main Thread) Profile dev activated. Live Coding activated.
    2024-04-03 18:51:43,521 INFO  [io.quarkus] (Quarkus Main Thread) Installed features: [cdi, mongodb-client, mongodb-panache, narayana-jta, rest, rest-jackson, smallrye-context-propagation, vertx]
    
    --
    Tests paused
    Press [e] to edit command line args (currently ''), [r] to resume testing, [o] Toggle test output, [:] for the terminal, [h] for more options>

Enter "r" - the tests will execute and print the following lines on the console

    All 2 tests are passing (0 skipped), 2 tests were run in 5445ms. Tests completed at 19:00:22.
    Press [e] to edit command line args (currently ''), [r] to re-run, [o] Toggle test output, [:] for the terminal, [h] for more options>


## Build  Docker Image

1. Build the project

```
./mvnw package
```

2. Run command to to build Docker image

```
    docker build -f src/main/Docker/Dockerfile.jvm -t documentdb-quarkus-panache-quickstart-jvm .
```

## Test Docker Image

3. Run command to create a local container running on this image we just created

```
    docker run -i --rm -p 8080:8080 documentdb-quarkus-panache-quickstart-jvm
```

1. [SSH](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-to-linux-instance.html) into a new terminal of the EC2 instance

3. Check if container is running

```
    docker ps
```

Output

    CONTAINER ID   IMAGE                                       COMMAND                  CREATED             STATUS             PORTS                                                 NAMES
    5efcc87496a9   quarkus/documentdb-panache-quickstart-jvm   "/bin/sh -c 'Java -D…"   About an hour ago   Up About an hour   5005/tcp, 0.0.0.0:8080->8080/tcp, :::8080->8080/tcp   cool_booth

1. Insert a document into person collection in DocumentDB using the repository methods

```
    curl -d '{ "name" : "moncef", "birthDate" : "1993-05-19", "status" : "LIVING"}' -H "Content-Type: application/json" -X POST http://localhost:8080/repository/persons
```
	
2. Get all documents from person collection in DocumentDB using the repository methods. You will notice the document, we just inserted, in the response.

```
    curl http://localhost:8080/repository/persons
```
	
3. Delete all documents from person collection in DocumentDB using the repository methods

```
    curl -X DELETE http://localhost:8080/repository/persons
```
	
2. Get all documents from person collection in DocumentDB using the repository methods. This time the response should be empty.

```
    curl http://localhost:8080/repository/persons
```





