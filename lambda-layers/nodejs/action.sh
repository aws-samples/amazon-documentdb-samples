#!/bin/bash

: "${AWS_ACCESS_KEY_ID:?Need to set AWS_ACCESS_KEY_ID non-empty}"
: "${AWS_SECRET_ACCESS_KEY:?Need to set AWS_SECRET_ACCESS_KEY non-empty}"
: "${AWS_DEFAULT_REGION:?Need to set AWS_DEFAULT_REGION non-empty}"

LAYER_NAME=documentdb-nodejs
RUNTIMES="nodejs14.x nodejs12.x"
PACKAGES="mongodb mongoose"
WORKDIR=/tmp/nodejs
PEMFILE="https://s3.amazonaws.com/rds-downloads/rds-combined-ca-bundle.pem"

#exports.handler = async function (event, context, callback) {
#    try {
#
#        var MongoClient = require('mongodb').MongoClient;
#
#        var f = require('util').format;
#        var fs = require('fs');
#
#        //Specify the Amazon DocumentDB cert
#        var ca = [fs.readFileSync("/opt/nodejs/rds-combined-ca-bundle.pem")];
#
#        //Create a MongoDB client, open a connection to Amazon DocumentDB as a replica set, 
#        //  and specify the read preference as secondary preferred
#
#        var client = await MongoClient.connect(
#        'mongodb://username:password@sample-cluster.node.us-east-1.docdb.amazonaws.com:27017/sample-database?ssl=true&replicaSet=rs0&readPreference=secondaryPreferred', 
#        { 
#          sslValidate: true,
#          sslCA:ca,
#          useNewUrlParser: true
#        });
#    
#        //Specify the database to be used
#        var db = client.db('sample-database');
#            
#        //Specify the collection to be used
#        var col = db.collection('sample-collection');
#    
#        var result = await col.findOne({});
#    
#        //Print the result to the screen
#        console.log(result);
#                
#        //Close the connection
#        client.close()
#        const response = {
#            statusCode: 200,
#            body: JSON.stringify(result),
#        };
#        return callback(null, response);
#    } catch (err) {
#        console.error("Error " + err);
#        console.error(err.stack);    
#        return callback(err);
#    }
#};

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

