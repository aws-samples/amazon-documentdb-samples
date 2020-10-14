#!/bin/bash

: "${AWS_ACCESS_KEY_ID:?Need to set AWS_ACCESS_KEY_ID non-empty}"
: "${AWS_SECRET_ACCESS_KEY:?Need to set AWS_SECRET_ACCESS_KEY non-empty}"
: "${AWS_DEFAULT_REGION:?Need to set AWS_DEFAULT_REGION non-empty}"

LAYER_NAME=documentdb-python
RUNTIMES="python2.7 python3.6 python3.7 python3.8"
PACKAGES="pymongo motor"
WORKDIR=/tmp/python
PEMFILE="https://s3.amazonaws.com/rds-downloads/rds-combined-ca-bundle.pem"

# Add this to connection string;
#  ?ssl=true&ssl_ca_certs=/opt/python/rds-combined-ca-bundle.pem

case $1 in
    "deploy") 
        rm -rf $WORKDIR
        mkdir -p $WORKDIR
        PYTHONUSERBASE=$WORKDIR python2.7 -m pip install --user $PACKAGES
        PYTHONUSERBASE=$WORKDIR python3.6 -m pip install --user $PACKAGES
        PYTHONUSERBASE=$WORKDIR python3.7 -m pip install --user $PACKAGES
        PYTHONUSERBASE=$WORKDIR python3.8 -m pip install --user $PACKAGES
        wget -O $WORKDIR/rds-combined-ca-bundle.pem $PEMFILE
        cd /tmp && zip -r layer-documentdb-python.zip python
        aws lambda publish-layer-version --layer-name $LAYER_NAME --compatible-runtimes $RUNTIMES --description "Layer for PyMongo, Motor and RDS PEM file" --zip-file fileb:///tmp/layer-documentdb-python.zip
        ;;
    "undeploy")
        versions=$(aws lambda list-layer-versions --layer-name $LAYER_NAME --output text | grep '^LAYERVERSIONS' | awk 'BEGIN { FS = "[\t]+" } ; { print $5 }')
        for v in ${versions[@]}
        do
            echo "We will undeploy version $v"
            aws lambda delete-layer-version --layer-name $LAYER_NAME --version-number $v
        done
        ;;
    "shell")
        echo "Run 'docker exec -it run_shell_documentdb_lambda_layers_python /bin/bash'"
        echo "Press [CTRL+C] to stop.."
        while true
        do
            sleep 1
        done
        ;;
    *)
        echo "Usage: $0 <deploy | undeploy | shell>"
        ;;
esac

