# How to Use Amazon DocumentDB with Rust - A Step-by-Step Guide
## Introduction

This sample project will create a Rust application that executes CRUD operations on an existing Amazon DocumentDB cluster. It will use AWS Secretes Manager to retrieve database credentials and connect to the Amazon DocumentDB cluster.

Project contains a `Cargo.toml` file with required dependencies and `main.rs` contains the main source code in Rust programming language.

## Prerequisites

You should have an existing Amazon DocumentDB cluster in your AWS account. Also needed is an EC2 instance that can connect to the DocumentDB cluster. Follow [Getting started with <link>Amazon DocumentDB (with MongoDB compatibility); Part 1 – using Amazon EC2](https://aws.amazon.com/blogs/database/part-1-getting-started-with-amazon-documentdb-using-amazon-ec2/) for detailed steps on creating a cluster and connecting to it from an Amazon EC2 instance.



Finally, you will need to store the database credentials in AWS Secretes Manager. For more information on how to create a secret refer to [AWS Secrets Manager user guide](https://docs.aws.amazon.com/secretsmanager/latest/userguide/create_secret.html). The secret name created in this step will be used later in the setup.

## Step 1: Setup on EC2 instance

The On the EC2 instance, Rust should be installed. Follow installation steps at [Install Rust](https://www.rust-lang.org/tools/install). Validate the Rust installation by running `rustc --version`.

Using below git command, clone repository in to the home directory of your EC2 instance.
```
git clone https://github.com/goyalnikhil/documentdb-rust.git
```
Also, download the AWS RDS global certificates bundle and save it your preferred location on your EC2 instance. Full path to this certificate will be needed later on.
```
wget https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
```

## Step 2: Update Rust source code

While in the `documentdb-rust` folder, open `src/main.rs` file in your choice of editor and make changes by replacing:
- `<Your-Seceret-Name>` with the name of secrete you created in AWS Secretes Manager with DocumentDB credentials.
- `<Path-to-global-bundle>` with the full path name of the location you stored the downloaded `global-bundle.pem` file.
Save the file and exit the editor. Your Rust code is ready to compile and run.

## Step 3: Build the application code

We will use Rust's inbuilt package manager `cargo` for compiling, building, and running the application. While still in the `documentdb-rust` folder, run command listed below. `cargo` will download the needed packages, compile them, and finally build a binary for the source code in the `src` folder. This could take a while.
```
cargo build
```

## Step 4: Run the sample app

The `cargo` package manager also allows us to run the application. From the command prompt while still in `documentdb-rust` folder, run below command to execute the application while passing command line argument to invoke each CRUD operation. 

#### 'C'reate document
Passing a command line argument `c` creats a document, you can use below command.

```
cargo r -- c
```

This should generate output similar to below.

```
[ec2-user@ip-xxxxxxxxx documentdb-rust]$ cargo r -- c
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.22s
     Running `target/debug/documentdb-rust c`
Connected to Amazon DocumentDB using credentials from Secrets Manager!
 Ping respose: { "ok": 1, "operationTime": Timestamp(1730126391, 1) }
Document inserted!
```
The created document can be viewed by running qurey via mongo shell against the database.

#### 'R'ead the created document
Passing a command line argument `r` reads the document, you can use below command.

```
cargo r -- r
```

This should generate output similar to below.

```
[ec2-user@ip-xxxxxxxxx documentdb-rust]$ cargo r -- r
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.28s
     Running `target/debug/documentdb-rust r`
Connected to Amazon DocumentDB using credentials from Secrets Manager!
 Ping respose: { "ok": 1, "operationTime": Timestamp(1730137680, 1) }
Some(
    Document({
        "_id": ObjectId(
            "671fa23741869db597dd0c04",
        ),
        "name": String(
            "Alice",
        ),
        "age": Int32(
            30,
        ),
        "city": String(
            "Seattle",
        ),
    }),
)
```

#### 'U'pdate the document
Passing a command line argument `u` updates the document, you can use below command.

```
cargo r -- u
```

This shdould generate output similar to below.

```
[ec2-user@ip-xxxxxxxx documentdb-rust]$ cargo r -- u
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.22s
     Running `target/debug/documentdb-rust u`
Connected to Amazon DocumentDB using credentials from Secrets Manager!
 Ping respose: { "ok": 1, "operationTime": Timestamp(1730145700, 1) }
Document updated!
```
The updated document can be viewed by running qurey via mongo shell against the database.

#### 'D'elete the created document
Passing a command line argument `d` reads the document, you can use below command.

```
cargo r -- d
```

This should generate output similar to below.

```
[ec2-user@ip-xxxxxxxx documentdb-rust]$ cargo r -- d
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.20s
     Running `target/debug/documentdb-rust d`
Connected to Amazon DocumentDB using credentials from Secrets Manager!
 Ping respose: { "ok": 1, "operationTime": Timestamp(1730145950, 1) }
Document deleted!
```
