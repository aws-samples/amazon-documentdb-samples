// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { CustomRule, ManagedRule, ManagedRuleIdentifiers, ResourceType, RuleScope } from '@aws-cdk/aws-config';
import { Rule } from '@aws-cdk/aws-events';
import { Effect, ManagedPolicy, PolicyStatement, Role, ServicePrincipal } from '@aws-cdk/aws-iam';
import { Code, Function, Runtime } from '@aws-cdk/aws-lambda';
import { Topic } from '@aws-cdk/aws-sns';
import { LogGroup, RetentionDays } from '@aws-cdk/aws-logs';
import * as cdk from '@aws-cdk/core';
import { CloudWatchLogGroup, LambdaFunction, SnsTopic } from '@aws-cdk/aws-events-targets';

interface DocumentDbConfigStackProps extends cdk.StackProps {
  clusterParameterGroup?: string;
  backupRetentionPeriod?: number;
}

export class AmazonDocumentdbAwsConfigStack extends cdk.Stack {
  constructor(scope: cdk.Construct, id: string, props?: DocumentDbConfigStackProps) {
    super(scope, id, props);

    const clusterParameterGroup = props?.clusterParameterGroup || 'blogpost-param-group';
    const backupRetentionPeriod = props?.backupRetentionPeriod || 7;

    // aws managed rules
    new ManagedRule(this, 'ClusterDeletionProtectionEnabled', {
      identifier: ManagedRuleIdentifiers.RDS_CLUSTER_DELETION_PROTECTION_ENABLED,
      configRuleName: 'documentdb-cluster-deletion-protection-enabled',
      ruleScope: RuleScope.fromResources([ResourceType.RDS_DB_CLUSTER])
    });

    new ManagedRule(this, 'StorageEncrypted', {
      identifier: ManagedRuleIdentifiers.RDS_STORAGE_ENCRYPTED,
      configRuleName: 'documentdb-cluster-storage-encrypted',
      ruleScope: RuleScope.fromResources([ResourceType.RDS_DB_INSTANCE])
    });

    // custom rules
    // cluster parameter group
    const clusterParameterGroupRole = new Role(this, 'ClusterParameterGroupRole', {
      assumedBy: new ServicePrincipal('lambda.amazonaws.com')
    }); 
    clusterParameterGroupRole.addManagedPolicy(ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'));
    clusterParameterGroupRole.addManagedPolicy(ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSConfigRulesExecutionRole'));

    const clusterParameterGroupFn = new Function(this, 'ClusterParameterGroupFn', {
      runtime: Runtime.NODEJS_14_X,
      handler: 'index.handler',
      code: Code.fromAsset('./lib/functions/cluster-parameter-group-rule'),
      role: clusterParameterGroupRole
    });

    new CustomRule(this, 'ClusterParameterGroupRule', {
      lambdaFunction: clusterParameterGroupFn,
      configurationChanges: true,
      configRuleName: 'documentdb-cluster-parameter-group',
      description: 'Evaluates whether the cluster parameter group is the one provided to the rule as a parameter',
      ruleScope: RuleScope.fromResources([ResourceType.RDS_DB_CLUSTER]),
      inputParameters: {
        desiredClusterParameterGroup: clusterParameterGroup
      }
    });

    // cluster backup retention
    const clusterBackupRententionRole = new Role(this, 'ClusterBackupRetentionRole', {
      assumedBy: new ServicePrincipal('lambda.amazonaws.com')
    }); 
    clusterBackupRententionRole.addManagedPolicy(ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'));
    clusterBackupRententionRole.addManagedPolicy(ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSConfigRulesExecutionRole'));

    const clusterBackupRetentionFn = new Function(this, 'ClusterBackupRetentionFn', {
      runtime: Runtime.NODEJS_14_X,
      handler: 'index.handler',
      code: Code.fromAsset('./lib/functions/cluster-backup-retention-rule'),
      role: clusterBackupRententionRole
    });

    new CustomRule(this, 'ClusterBackupRetentionRule', {
      lambdaFunction: clusterBackupRetentionFn,
      configurationChanges: true,
      configRuleName: 'documentdb-cluster-backup-retention',
      description: 'Evaluates whether the backup retention policy has been set to a greater value than the one provided to the as parameter',
      ruleScope: RuleScope.fromResources([ResourceType.RDS_DB_CLUSTER]),
      inputParameters: {
        minBackupRetentionPeriod: backupRetentionPeriod
      }
    });

    // instances homogeneous
    const instancesHomogeneousRole = new Role(this, 'InstancesHomogeneousRole', {
      assumedBy: new ServicePrincipal('lambda.amazonaws.com')
    }); 
    instancesHomogeneousRole.addManagedPolicy(ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'));
    instancesHomogeneousRole.addManagedPolicy(ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSConfigRulesExecutionRole'));
    instancesHomogeneousRole.addToPolicy(new PolicyStatement({
      effect: Effect.ALLOW,
      actions: ['rds:DescribeDBInstances'],
      resources: ['*']
    }));

    const instancesHomogeneousFn = new Function(this, 'InstancesHomogeneousFn', {
      runtime: Runtime.NODEJS_14_X,
      handler: 'index.handler',
      code: Code.fromAsset('./lib/functions/instances-homogeneous-rule'),
      role: instancesHomogeneousRole
    });

    new CustomRule(this, 'InstancesHomogeneousRule', {
      lambdaFunction: instancesHomogeneousFn,
      configurationChanges: true,
      configRuleName: 'documentdb-cluster-instances-homogeneous',
      description: 'Evaluates whether all instances within an Amazon DocumentDB cluster belong to the same instance family and size.',
      ruleScope: RuleScope.fromResources([ResourceType.RDS_DB_INSTANCE])
    });

    // remediation
    // sns topic for notifications
    const topic = new Topic(this, 'ComplianceNotificationsTopic', {
      displayName: 'Compliance Notifications'
    });

    // cloudwatch log group for debugging purposes
    const logGroup = new LogGroup(this, 'AuditLogGroup', {
      logGroupName: `/aws/events/documentdb-config-events`,
      retention: RetentionDays.ONE_WEEK
    });

    const notificationRule = new Rule(this, 'ComplianceNotificationRule', {
      eventPattern: {
        source: ['aws.config'],
        detailType: ['Config Rules Compliance Change'],
        detail: {
          messageType: ['ComplianceChangeNotification'],
          newEvaluationResult: {
            complianceType: ['NON_COMPLIANT'],
            evaluationResultIdentifier: {
              evaluationResultQualifier: {
                configRuleName: [{prefix: 'documentdb-'}]
              }
            }
          },
          resourceType: ['AWS::RDS::DBCluster', 'AWS::RDS::DBInstance']
        }
      }
    });

    notificationRule.addTarget(new CloudWatchLogGroup(logGroup));
    notificationRule.addTarget(new SnsTopic(topic));

    // paramater group remediation
    // (the IAM role below can be shared among both lambda functions that remediate
    // wrong parameter group and deletion protection disabled as they both perform the
    // same operations and thus require same IAM permissions with current implementation)
    const remediationRole = new Role(this, 'ParameterGroupRemediationRole', {
      assumedBy: new ServicePrincipal('lambda.amazonaws.com')
    }); 
    remediationRole.addManagedPolicy(ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'));
    remediationRole.addToPolicy(new PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'rds:DescribeDBClusters',
        'rds:ModifyDBCluster'
      ],
      resources: ['*']
    }));

    const parameterGroupRemediationFn = new Function(this, 'ParameterGroupRemediationFn', {
      runtime: Runtime.NODEJS_14_X,
      handler: 'index.handler',
      code: Code.fromAsset('./lib/functions/cluster-parameter-group-remediation'),
      role: remediationRole,
      environment: {
        DESIRED_CLUSTER_PARAMETER_GROUP: clusterParameterGroup
      }
    });

    const parameterGroupRule = new Rule(this, 'ParameterGroupRule', {
      eventPattern: {
        source: ['aws.config'],
        detailType: ['Config Rules Compliance Change'],
        detail: {
          messageType: ['ComplianceChangeNotification'],
          newEvaluationResult: {
            evaluationResultIdentifier: {
              evaluationResultQualifier: {
                configRuleName: ['documentdb-cluster-parameter-group']
              }
            },
            complianceType: ['NON_COMPLIANT']
          },
          resourceType: ['AWS::RDS::DBCluster']
        }
      }
    });

    parameterGroupRule.addTarget(new LambdaFunction(parameterGroupRemediationFn));

    // cluster deletion protection remediation
    const deletionProtectionRemediationFn = new Function(this, 'DeletionProtectionRemediationFn', {
      runtime: Runtime.NODEJS_14_X,
      handler: 'index.handler',
      code: Code.fromAsset('./lib/functions/cluster-deletion-protection-remediation'),
      role: remediationRole
    });

    const deletionProtectionRule = new Rule(this, 'DelectionProtectionRule', {
      eventPattern: {
        source: ['aws.config'],
        detailType: ['Config Rules Compliance Change'],
        detail: {
          messageType: ['ComplianceChangeNotification'],
          newEvaluationResult: {
            evaluationResultIdentifier: {
              evaluationResultQualifier: {
                configRuleName: ['documentdb-cluster-deletion-protection-enabled']
              }
            },
            complianceType: ['NON_COMPLIANT']
          },
          resourceType: ['AWS::RDS::DBCluster']
        }
      }
    });

    deletionProtectionRule.addTarget(new LambdaFunction(deletionProtectionRemediationFn));
  }
}
