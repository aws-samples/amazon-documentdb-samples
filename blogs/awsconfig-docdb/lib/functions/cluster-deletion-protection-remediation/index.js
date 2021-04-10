// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

const aws = require('aws-sdk');
const docDb = new aws.DocDB();

exports.handler = async event => {
  try {
    const {detail: {resourceId}} = event;
    const dbClusterIdentifier = await getDbClusterIdentifier(resourceId);
    const params = {
      DBClusterIdentifier: dbClusterIdentifier,
      DeletionProtection: true
    };

    await docDb.modifyDBCluster(params).promise();
    return;

  } catch (e) {
    console.log('There has been an error', e);
    throw e;
  }
};

async function getDbClusterIdentifier(resourceId) {
  try {
    const {DBClusters: clusters} = await docDb.describeDBClusters().promise();  
    const {DBClusterIdentifier: dbClusterIdentifier} = clusters.find(c => c.DbClusterResourceId === resourceId);

    if (!dbClusterIdentifier) {
      throw new Error(`Cluster with resourceId=${resourceId} not found`);
    }

    return dbClusterIdentifier;

  } catch (e) {
    console.log(e);
    throw e;
  }
}