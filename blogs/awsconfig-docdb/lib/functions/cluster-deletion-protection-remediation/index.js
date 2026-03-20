// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

const { DocDBClient, DescribeDBClustersCommand, ModifyDBClusterCommand } = require('@aws-sdk/client-docdb');
const docDb = new DocDBClient();

exports.handler = async event => {
  try {
    const {detail: {resourceId}} = event;
    const dbClusterIdentifier = await getDbClusterIdentifier(resourceId);
    const params = {
      DBClusterIdentifier: dbClusterIdentifier,
      DeletionProtection: true
    };

    const command = new ModifyDBClusterCommand(params);
    await docDb.send(command);
    return;

  } catch (e) {
    console.log('There has been an error', e);
    throw e;
  }
};

async function getDbClusterIdentifier(resourceId) {
  try {
    const command = new DescribeDBClustersCommand({});
    const {DBClusters: clusters} = await docDb.send(command);
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