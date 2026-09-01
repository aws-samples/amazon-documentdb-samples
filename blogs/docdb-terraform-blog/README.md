# Provision a Secure Amazon DocumentDB Cluster with Terraform

This repository contains Terraform configuration to deploy a secure [Amazon DocumentDB](https://aws.amazon.com/documentdb/) cluster with MongoDB compatibility, implementing comprehensive security controls.

## Features

- **Amazon DocumentDB**: Support for drivers compatible with MongoDB API versions 6.0, 7.0, and 8.0
- **Network isolation**: Private subnets with no internet access, restrictive security groups
- **Encryption at rest**: Customer-managed AWS KMS keys for cluster data, logs, and parameters
- **Encryption in transit**: TLS enforced via cluster parameter group
- **Managed credentials**: AWS Secrets Manager integration (password never in Terraform state)
- **Monitoring**: Encrypted CloudWatch audit and profiler logs, Performance Insights enabled
- **High availability**: Multi-AZ deployment with 2 instances across Availability Zones
- **Infrastructure outputs**: Stored as encrypted JSON in AWS Systems Manager Parameter Store

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.0
- AWS Provider 6.44.0
- AWS CLI configured with appropriate credentials and region
- Permissions to create VPC, DocumentDB, KMS, Secrets Manager, CloudWatch, SSM, and IAM resources

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/aws-samples/amazon-documentdb-samples.git
   cd amazon-documentdb-samples/blogs/docdb-terraform-blog
   ```

2. Initialize and deploy:
   ```bash
   terraform init
   terraform apply
   ```

3. Verify the deployment:
   ```bash
   aws docdb describe-db-clusters \
     --db-cluster-identifier docdb-terraform-demo \
     --query 'DBClusters[0].{Status:Status,EngineVersion:EngineVersion,StorageEncrypted:StorageEncrypted}'
   ```

4. Connect to your cluster:

   For detailed instructions on connecting to your Amazon DocumentDB cluster, including driver configuration, TLS certificate setup, and connection string options, see [Connecting to Amazon DocumentDB](https://docs.aws.amazon.com/documentdb/latest/devguide/connect-docdb.html).

## Project Structure

```
.
├── documentdb.tf          # DocumentDB cluster, instances, parameter group, subnet group
├── kms.tf                 # KMS key and policy for DocumentDB encryption
├── logs.tf                # KMS key and encrypted CloudWatch log groups
├── ssm.tf                 # KMS key and SSM Parameter Store for outputs
├── network.tf             # Module call to network/
├── variables.tf           # Input variables with validation
├── outputs.tf             # Terraform outputs
├── provider.tf            # Provider configuration (AWS 6.44.0)
├── .gitignore             # Terraform-specific ignores
└── network/               # Reusable network module
    ├── network.tf         # VPC, private subnets, route table
    ├── security_group.tf  # Default SG disabled, custom SG for DocumentDB
    ├── endpoints.tf       # Interface VPC endpoints (Secrets Manager, SSM, CloudWatch Logs)
    ├── output.tf          # Module outputs
    ├── provider.tf        # Module provider requirements
    └── variables.tf       # Module input variables
```

## Security Controls

| Layer | Implementation |
|-------|---------------|
| Network | Private subnets, no IGW/NAT, default SG disabled, egress restricted to VPC CIDR |
| Encryption at rest | Customer-managed KMS key with explicit key policy and rotation enabled |
| Encryption in transit | TLS 1.2+ enforced via `tls = tls1.2+` parameter |
| Authentication | `manage_master_user_password = true` — AWS manages password in Secrets Manager |
| Logging | Audit + profiler logs to KMS-encrypted CloudWatch log groups (audit 365-day, profiler 30-day retention) |
| Monitoring | Performance Insights enabled with KMS encryption |
| Outputs | Infrastructure values stored as encrypted SecureString in SSM Parameter Store |

## Customization

Override default values by passing variables:

```bash
terraform apply \
  -var="name=my-docdb-cluster" \
  -var="region=us-west-2" \
  -var="instance_class=db.r6g.large" \
  -var="instance_count=3"
```

See `variables.tf` for all configurable parameters.

## Cleanup

```bash
terraform apply -var="deletion_protection=false" -var="skip_final_snapshot=true"
terraform destroy
```

## Related Blog Post

This code accompanies the AWS Database Blog post: [Provision a secure Amazon DocumentDB cluster with Terraform](https://aws.amazon.com/blogs/database/provision-a-secure-amazon-documentdb-cluster-with-terraform/).

## Security

See [CONTRIBUTING](../../CONTRIBUTING.md) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](../../LICENSE) file.
