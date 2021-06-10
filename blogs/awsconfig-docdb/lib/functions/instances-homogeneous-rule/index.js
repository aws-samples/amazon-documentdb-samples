// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

const aws = require('aws-sdk');
const config = new aws.ConfigService();
const docDb = new aws.DocDB();

// helper function used to validate input
function checkDefined(reference, referenceName) {
  if (!reference) {
    throw new Error(`Error: ${referenceName} is not defined`);
  }
  return;
}

// check whether the message is OversizedConfigurationItemChangeNotification or not
// (for more details see https://docs.aws.amazon.com/config/latest/APIReference/API_SourceDetail.html)
function isOverSizedChangeNotification(messageType) {
  checkDefined(messageType, 'messageType');
  return messageType === 'OversizedConfigurationItemChangeNotification';
}

// Get configurationItem using getResourceConfigHistory API
async function getConfiguration(resourceType, resourceId, configurationCaptureTime) {
  try {
    const laterTime = new Date(configurationCaptureTime);
    const data = await config.getResourceConfigHistory({ resourceType, resourceId, laterTime, limit: 1 }).promise();
    const configurationItem = data.configurationItems[0];
    return configurationItem;
  } catch (e) {
    console.log('There has been an error whil getting Resource Config History', e);
    throw e;
  }
}

// convert from the API model to the original invocation model
/*eslint no-param-reassign: ["error", { "props": false }]*/
function convertApiConfiguration(apiConfiguration) {
  apiConfiguration.awsAccountId = apiConfiguration.accountId;
  apiConfiguration.ARN = apiConfiguration.arn;
  apiConfiguration.configurationStateMd5Hash = apiConfiguration.configurationItemMD5Hash;
  apiConfiguration.configurationItemVersion = apiConfiguration.version;
  apiConfiguration.configuration = JSON.parse(apiConfiguration.configuration);
  if ({}.hasOwnProperty.call(apiConfiguration, 'relationships')) {
    for (let i = 0; i < apiConfiguration.relationships.length; i++) {
      apiConfiguration.relationships[i].name = apiConfiguration.relationships[i].relationshipName;
    }
  }
  return apiConfiguration;
}

// based on the type of message get the configuration item either
// from configurationItem in the invoking event or using the 
// getResourceConfigHistory API in getConfiguration function
async function getConfigurationItem(invokingEvent) {
  try {
    checkDefined(invokingEvent, 'invokingEvent');
    if (isOverSizedChangeNotification(invokingEvent.messageType)) {
      const configurationItemSummary = checkDefined(invokingEvent.configurationItemSummary, 'configurationItemSummary');
      const apiConfigurationItem = await getConfiguration(configurationItemSummary.resourceType, configurationItemSummary.resourceId, configurationItemSummary.configurationItemCaptureTime);
      
      const configurationItem = convertApiConfiguration(apiConfigurationItem);
      return configurationItem;
    } else {
      checkDefined(invokingEvent.configurationItem, 'configurationItem');
      return invokingEvent.configurationItem;
    } 
  } catch (e) {
    console.log('Error while getting the configuration for the resource', e);
    throw e;
  }
}

// check whether the resource is a documentdb cluster or it
// has been deleted and if it has, then the evaluation is unnecessary
function isApplicable(configurationItem, event) {
  checkDefined(configurationItem, 'configurationItem');
  
  // if eventLeftScope is true the resource to be evaluated has been removed
  // https://docs.aws.amazon.com/config/latest/developerguide/evaluate-config_develop-rules_example-events.html
  const eventLeftScope = event.eventLeftScope;
  if (eventLeftScope) {
    return false;
  }

  checkDefined(configurationItem.configuration, 'configurationItem.configuration');
  if (configurationItem.resourceType !== 'AWS::RDS::DBInstance' || configurationItem.configuration.engine !== 'docdb') {
    console.log('This is not a DocumentDB instance');
    return false;
  }

  const status = configurationItem.configurationItemStatus;  
  return (status === 'OK' || status === 'ResourceDiscovered') && eventLeftScope === false;
}

// evaluate if all cluster instances belong to the same instance family and size
async function evaluateChangeNotificationCompliance(configurationItem, dbClusterInstances) {
  if (dbClusterInstances.length === 1) {
    return 'COMPLIANT';
  }

  checkDefined(configurationItem, 'configurationItem');
  checkDefined(configurationItem.configuration, 'configurationItem.configuration');
  
  const newDBInstanceClass = configurationItem.configuration.pendingModifiedValues.dBInstanceClass;
  
  let sameDBInstanceClass = true;
  if (newDBInstanceClass) {
    for (let i = 0; i < dbClusterInstances.length; i++) {
      const dbInstance = dbClusterInstances[i];
  
      // skip instance being modified
      if(dbInstance.DBInstanceIdentifier === configurationItem.configuration.dBInstanceIdentifier) {
        continue;
      }
  
      if (newDBInstanceClass !== dbInstance.DBInstanceClass) {
        sameDBInstanceClass = false;
        break;
      }
    } 
  } else {
    // just check all db instance classes are equal
    sameDBInstanceClass = dbClusterInstances.every(i => i.DBInstanceClass === dbClusterInstances[0].DBInstanceClass);
  }

  return sameDBInstanceClass ? 'COMPLIANT' : 'NON_COMPLIANT';
}

async function getClusterInstances(configurationItem) {
  checkDefined(configurationItem.configuration.dBClusterIdentifier, 'configurationItem.configuration.dBClusterIdentifier');

  const params = {
    Filters: [{
      Name: 'db-cluster-id',
      Values: [configurationItem.configuration.dBClusterIdentifier]
    }]
  };
  const {DBInstances: dbClusterInstances} = (await docDb.describeDBInstances(params).promise());
  return dbClusterInstances;
}

exports.handler = async event => {
  checkDefined(event, 'event');
  const invokingEvent = JSON.parse(event.invokingEvent);
  try {

    const configurationItem = await getConfigurationItem(invokingEvent);
    
    let compliance = 'NOT_APPLICABLE';
    const putEvaluationsRequest = {
      Evaluations: []
    };
    let dbClusterInstances = [];

    // only evaluate rule for documentdb clusters
    if (isApplicable(configurationItem, event)) {
      // invoke the compliance checking function
      dbClusterInstances = await getClusterInstances(configurationItem);
      compliance = await evaluateChangeNotificationCompliance(configurationItem, dbClusterInstances);

      // update rule compliance status for all instances
      dbClusterInstances.forEach(i => {
        putEvaluationsRequest.Evaluations.push({
          ComplianceResourceType: configurationItem.resourceType,
          ComplianceResourceId: i.DbiResourceId,
          ComplianceType: compliance,
          OrderingTimestamp: configurationItem.configurationItemCaptureTime,
        });
      });
    } else {
      putEvaluationsRequest.Evaluations = [{
        ComplianceResourceType: configurationItem.resourceType,
        ComplianceResourceId: configurationItem.resourceId,
        ComplianceType: compliance,
        OrderingTimestamp: configurationItem.configurationItemCaptureTime,
      }];
    }
        
    putEvaluationsRequest.ResultToken = event.resultToken;

    // invoke the Config API to report the result of the evaluation
    let result;
    try {      
      result = await config.putEvaluations(putEvaluationsRequest).promise();
    } catch (e) {
      console.log('There has been an error while sending evaluations to AWS Config', e);
      throw e;
    }

    if (result.FailedEvaluations.length > 0) {
      throw new Error('Not all evaluations were successfully reported to AWS Config');
    }

    return result;
    
  } catch (e) {
    console.log('There has been an error', e);
    throw e;
  }  
};
