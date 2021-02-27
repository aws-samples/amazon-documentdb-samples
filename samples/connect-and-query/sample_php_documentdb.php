<?php
require 'vendor/autoload.php';

//Specify the Amazon DocumentDB cert
$ctx = stream_context_create(array(
    "ssl" => array(
        "cafile" => "/home/ubuntu/environment/rds-combined-ca-bundle.pem",
    ))
);

$data =  '[
{ "_id" : 1, "name" : "Tim", "status": "active", "level": 12, "score":202},
{ "_id" : 2, "name" : "Justin", "status": "inactive", "level": 2, "score":9},
{ "_id" : 3, "name" : "Beth", "status": "active", "level": 7, "score":87},
{ "_id" : 4, "name" : "Jesse", "status": "active", "level": 3, "score":27}
]';

$arraydata = json_decode($data);

//Reading credentials from environment variables
$username = getenv("username");
$password = getenv("password");
$clusterendpoint = getenv("clusterendpoint");
//Create a MongoDB client and open connection to Amazon DocumentDB
//Sample connection string format - mongodb://myusername:mypassword@testcluster.us-east-2.docdb.amazonaws.com:27017

$client = new MongoDB\Client("mongodb://".$username.":".$password."@".$clusterendpoint."/"."?"."retryWrites=false", array("ssl" => true), array("context" => $ctx));

$col = $client->sampledb->samplecoll;

//Insert a single document
$result = $col->insertMany( $arraydata );

//Find the document that was previously written
$result = $col->findOne(array('name' => 'Jesse'));
print_r($result);

$result = $col->updateOne(
    [ 'name' => 'Jesse' ],
    [ '$set' =>  [ 'level' => '4' ]]);
$result = $col->findOne(array('name' => 'Jesse'));
print_r($result);
$col->drop();
?>
