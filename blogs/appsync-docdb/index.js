const mongo = require('mongodb');
const fs = require('fs');
const AWS = require('aws-sdk');
const ca = [fs.readFileSync('/opt/nodejs/rds-combined-ca-bundle.pem')];

exports.handler =  async function(event, context) {
    console.log("Received event {}", JSON.stringify(event, 3));
    console.log("event.info.fieldName is:", event.info.fieldName)

    let query;
    let result;

    let client = await connectToDB();
    const db = client.db('friends');
    const collection = await db.collection("friendsEpisodes")

    switch(event.info.fieldName){
        case "getEpisode":
            query = event.arguments;
            result = await collection.findOne(query)
            return result
        case "allEpisodes":
            query = event.arguments;
            result = await collection.find().toArray();
            return result
    }
}

async function getSecretValue(){
    let sm = new AWS.SecretsManager()
    try{
        let secret = await sm.getSecretValue({SecretId: "Blog-DocdbSecret"}).promise()
        return secret['SecretString']
    }catch(e){
        return e;
    }
}

async function connectToDB() {

    let res = await getSecretValue();
    let credentials = JSON.parse(res)
    const DB_USERNAME = credentials['username'];
    const DB_PASSWORD = credentials['password'];
    const DB_HOST = credentials['host'];
    const DB_PORT = credentials['port'];
    const DB_URL = `mongodb://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}`

    let cacheClient = await mongo.MongoClient.connect(DB_URL, {
      ssl: true,
      sslValidate: true,
      sslCA: ca,
      useNewUrlParser: true,
      useUnifiedTopology: true
    });
    return cacheClient;
}