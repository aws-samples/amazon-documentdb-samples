// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { Construct } from 'constructs';
import { 
  aws_config as config,
  aws_events as events,
  aws_iam as iam,
  aws_lambda as lambda,
  aws_sns as sns,
  aws_logs as logs,
  aws_events_targets as targets,
  aws_kms as kms,
  Stack, StackProps
} from 'aws-cdk-lib';

interface DocumentDbConfigStackProps extends StackProps {
  clusterParameterGroup?: string;
  backupRetentionPeriod?: number;
}

export class AmazonDocumentdbAwsConfigStack extends Stack {
  constructor(scope: Construct, id: string, props?: DocumentDbConfigStackProps) {
    super(scope, id, props);

    const clusterParameterGroup = props?.clusterParameterGroup || 'blogpost-param-group';
    const backupRetentionPeriod = props?.backupRetentionPeriod || 7;

    // aws managed rules
    new config.ManagedRule(this, 'ClusterDeletionProtectionEnabled', {
      identifier: config.ManagedRuleIdentifiers.RDS_CLUSTER_DELETION_PROTECTION_ENABLED,
      configRuleName: 'documentdb-cluster-deletion-protection-enabled',
      ruleScope: config.RuleScope.fromResources([config.ResourceType.RDS_DB_CLUSTER])
    });

    new config.ManagedRule(this, 'StorageEncrypted', {
      identifier: config.ManagedRuleIdentifiers.RDS_STORAGE_ENCRYPTED,
      configRuleName: 'documentdb-cluster-storage-encrypted',
      ruleScope: config.RuleScope.fromResources([config.ResourceType.RDS_DB_INSTANCE])
    });

    // custom rules
    // cluster parameter group
    const clusterParameterGroupRole = new iam.Role(this, 'ClusterParameterGroupRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com')
    }); 
    clusterParameterGroupRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'));
    clusterParameterGroupRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSConfigRulesExecutionRole'));

    const clusterParameterGroupFn = new lambda.Function(this, 'ClusterParameterGroupFn', {
      runtime: lambda.Runtime.NODEJS_22_X,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('./lib/functions/cluster-parameter-group-rule'),
      role: clusterParameterGroupRole
    });

    new config.CustomRule(this, 'ClusterParameterGroupRule', {
      lambdaFunction: clusterParameterGroupFn,
      configurationChanges: true,
      configRuleName: 'documentdb-cluster-parameter-group',
      description: 'Evaluates whether the cluster parameter group is the one provided to the rule as a parameter',
      ruleScope: config.RuleScope.fromResources([config.ResourceType.RDS_DB_CLUSTER]),
      inputParameters: {
        desiredClusterParameterGroup: clusterParameterGroup
      }
    });

    // cluster backup retention
    const clusterBackupRententionRole = new iam.Role(this, 'ClusterBackupRetentionRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com')
    }); 
    clusterBackupRententionRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'));
    clusterBackupRententionRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSConfigRulesExecutionRole'));

    const clusterBackupRetentionFn = new lambda.Function(this, 'ClusterBackupRetentionFn', {
      runtime: lambda.Runtime.NODEJS_22_X,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('./lib/functions/cluster-backup-retention-rule'),
      role: clusterBackupRententionRole
    });

    new config.CustomRule(this, 'ClusterBackupRetentionRule', {
      lambdaFunction: clusterBackupRetentionFn,
      configurationChanges: true,
      configRuleName: 'documentdb-cluster-backup-retention',
      description: 'Evaluates whether the backup retention policy has been set to a greater value than the one provided to the as parameter',
      ruleScope: config.RuleScope.fromResources([config.ResourceType.RDS_DB_CLUSTER]),
      inputParameters: {
        minBackupRetentionPeriod: backupRetentionPeriod
      }
    });

    // instances homogeneous
    const instancesHomogeneousRole = new iam.Role(this, 'InstancesHomogeneousRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com')
    }); 
    instancesHomogeneousRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'));
    instancesHomogeneousRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSConfigRulesExecutionRole'));
    instancesHomogeneousRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['rds:DescribeDBInstances'],
      resources: ['*']
    }));

    const instancesHomogeneousFn = new lambda.Function(this, 'InstancesHomogeneousFn', {
      runtime: lambda.Runtime.NODEJS_22_X,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('./lib/functions/instances-homogeneous-rule'),
      role: instancesHomogeneousRole
    });

    new config.CustomRule(this, 'InstancesHomogeneousRule', {
      lambdaFunction: instancesHomogeneousFn,
      configurationChanges: true,
      configRuleName: 'documentdb-cluster-instances-homogeneous',
      description: 'Evaluates whether all instances within an Amazon DocumentDB cluster belong to the same instance family and size.',
      ruleScope: config.RuleScope.fromResources([config.ResourceType.RDS_DB_INSTANCE])
    });

    // remediation
    // sns topic for notifications
    const key = new kms.Key(this, 'Key');
    key.addToResourcePolicy(new iam.PolicyStatement({
      actions: [
        'kms:GenerateDataKey',
        'kms:Decrypt'
      ],
      principals: [new iam.ServicePrincipal('events.amazonaws.com')],
      resources: ['*'],
    }));

    const topic = new sns.Topic(this, 'ComplianceNotificationsTopic', {
      displayName: 'Compliance Notifications',
      masterKey: key
    });

    // cloudwatch log group for debugging purposes
    const logGroup = new logs.LogGroup(this, 'AuditLogGroup', {
      logGroupName: `/aws/events/documentdb-config-events`,
      retention: logs.RetentionDays.ONE_WEEK
    });

    const notificationRule = new events.Rule(this, 'ComplianceNotificationRule', {
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

    notificationRule.addTarget(new targets.CloudWatchLogGroup(logGroup));
    notificationRule.addTarget(new targets.SnsTopic(topic));

    // parameter group remediation
    // (the IAM role below can be shared among both lambda functions that remediate
    // wrong parameter group and deletion protection disabled as they both perform the
    // same operations and thus require same IAM permissions with current implementation)
    const remediationRole = new iam.Role(this, 'ParameterGroupRemediationRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com')
    }); 
    remediationRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'));
    remediationRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'rds:DescribeDBClusters',
        'rds:ModifyDBCluster'
      ],
      resources: ['*']
    }));

    const parameterGroupRemediationFn = new lambda.Function(this, 'ParameterGroupRemediationFn', {
      runtime: lambda.Runtime.NODEJS_22_X,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('./lib/functions/cluster-parameter-group-remediation'),
      role: remediationRole,
      environment: {
        DESIRED_CLUSTER_PARAMETER_GROUP: clusterParameterGroup
      }
    });

    const parameterGroupRule = new events.Rule(this, 'ParameterGroupRule', {
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

    parameterGroupRule.addTarget(new targets.LambdaFunction(parameterGroupRemediationFn));

    // cluster deletion protection remediation
    const deletionProtectionRemediationFn = new lambda.Function(this, 'DeletionProtectionRemediationFn', {
      runtime: lambda.Runtime.NODEJS_22_X,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('./lib/functions/cluster-deletion-protection-remediation'),
      role: remediationRole
    });

    const deletionProtectionRule = new events.Rule(this, 'DelectionProtectionRule', {
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

    deletionProtectionRule.addTarget(new targets.LambdaFunction(deletionProtectionRemediationFn));
  }
}
