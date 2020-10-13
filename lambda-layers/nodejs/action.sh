#!/bin/bash

: "${AWS_ACCESS_KEY_ID:?Need to set AWS_ACCESS_KEY_ID non-empty}"
: "${AWS_SECRET_ACCESS_KEY:?Need to set AWS_SECRET_ACCESS_KEY non-empty}"
: "${AWS_DEFAULT_REGION:?Need to set AWS_DEFAULT_REGION non-empty}"

LAYER_NAME=documentdb-nodejs
RUNTIMES="nodejs10.x nodejs12.x"
PACKAGES="mongodb mongoose"
WORKDIR=/tmp/nodejs
PEMFILE="https://s3.amazonaws.com/rds-downloads/rds-combined-ca-bundle.pem"

# CA file will be in /opt/nodejs
#var ca = [fs.readFileSync("/opt/nodejs/rds-combined-ca-bundle.pem")];

#var MongoClient = require('mongodb').MongoClient,
#  f = require('util').format,
#  fs = require('fs');
#
#var ca = [fs.readFileSync("/opt/nodejs/rds-combined-ca-bundle.pem")];
#
#var client = MongoClient.connect(
#'mongodb://<sample-user>:<password>@sample-cluster.node.us-east-1.docdb.amazonaws.com:27017/sample-database?ssl=true&replicaSet=rs0&readPreference=secondaryPreferred', 
#{ 
#  sslValidate: true,
#  sslCA:ca,
#  useNewUrlParser: true
#},
#function(err, client) {
#    if(err)
#        throw err;
#        
#    db = client.db('sample-database');
#    
#    col = db.collection('sample-collection');
#
#    col.insertOne({'hello':'Amazon DocumentDB'}, function(err, result){
#      col.findOne({'hello':'Amazon DocumentDB'}, function(err, result){
#        console.log(result);
#        
#        client.close()
#      });
#   });
#});

case $1 in
    "deploy") 
        rm -rf $WORKDIR
        mkdir -p $WORKDIR
        npm --prefix $WORKDIR install $PACKAGES
        rm -f $WORKDIR/package-lock.json
        wget -O $WORKDIR/rds-combined-ca-bundle.pem $PEMFILE
        cd /tmp && zip -r layer-documentdb-nodejs.zip nodejs
        aws lambda publish-layer-version --layer-name $LAYER_NAME --compatible-runtimes $RUNTIMES --description "Layer for PyMongo, Motor and RDS PEM file" --zip-file fileb:///tmp/layer-documentdb-nodejs.zip
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
        echo "Run 'docker exec -it run_shell_documentdb_lambda_layers_nodejs /bin/bash'"
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

