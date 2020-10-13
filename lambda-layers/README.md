# Project Title

Amazon DocumentDB Lambda Layers has sample scripts for building and deploying custom [Lambda Layers](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html) containing prerequisite language libraries and the [RDS CA Certificate](https://docs.aws.amazon.com/documentdb/latest/developerguide/connect_programmatically.html#connect_programmatically-tls_enabled) used for connecting to DocumentDB.

There are samples for Python and Node.js

## Getting Started

These instructions will get you a copy of the project up and running in your AWS account. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

In practice you might want to modify the layer names used by the relevant action.sh scripts to be more meaningful to your organization.

A Dockerfile is included for each language binding which allows you to easily deploy the samples into your own account without having to install any prerequisites besides the docker toolchain.  You must have the following 3 environment variables defined when executing these docker images:

* AWS_ACCESS_KEY_ID
* AWS_SECRET_ACCESS_KEY
* AWS_DEFAULT_REGION

These environment variables will define which AWS account and region the layer is deployed to.

### Copying the process into your own code

If you want to recreate this process in your own repository, dive into the action.sh scripts for each language which show you how to package the zip file and deploy it as a lambda layer.

* [Python action.sh](python/action.sh)
* [Node.js action.sh](nodejs/action.sh)

### Installing using Docker

#### Installing Python Layer

All the following commands assume you've installed docker on your system and have exported the AWS environment variables.

To deploy the Python Lambda Layer:

```
bash deploy_python.sh
```

You can also remove ALL Python Lambda Layers:

```
bash undeploy_python.sh
```

If you want to test out the deployment by running a shell inside the docker container, use the run_shell_nodejs.sh script

```
bash run_shell_python.sh
```

In another window you can drop into a shell inside the docker container:

```
docker exec -it run_shell_documentdb_lambda_layers_python /bin/bash
cd /tmp
bash action.sh deploy
```

#### Installing Node.js Layer

All the following commands assume you've installed docker on your system and have exported the AWS environment variables.

To deploy the Node.js Lambda Layer:

```
bash deploy_nodejs.sh
```

You can also remove ALL Node.js Lambda Layers:

```
bash undeploy_nodejs.sh
```

If you want to test out the deployment by running a shell inside the docker container, use the run_shell_nodejs.sh script

```
bash run_shell_nodejs.sh
```

In another window you can drop into a shell inside the docker container:

```
docker exec -it run_shell_documentdb_lambda_layers_nodejs /bin/bash
cd /tmp
bash action.sh deploy
```
## License

This project is licensed under the MIT-0 License - see the [LICENSE](LICENSE) file for details
