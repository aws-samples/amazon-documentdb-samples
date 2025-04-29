# Amazon DocumentDB (with MongoDB compatibility) User Management with Terraform

This is an example of how to use the [AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs) in Terraform, along with [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/), to manage users in Amazon DocumentDB.

## Features

- Create and manage Amazon DocumentDB users with specific roles and permission
- Automatic user deletion when resources are destroyed
- Support for multiple database roles per user

## Prerequisites

- [AWS credentials](https://registry.terraform.io/providers/hashicorp/aws/latest/docs#authentication-and-configuration) configured
- Terraform v0.13+ installed
- `mongosh` client installed in the environment where Terraform runs (this is validated)
- Existing Amazon DocumentDB cluster
- [Amazon DocumentDB primary user credentials](https://docs.aws.amazon.com/documentdb/latest/developerguide/docdb-secrets-manager.html) managed in AWS Secrets Manager
- Executable permission set for `scripts/*.sh`

## Usage

```hcl
module "docdb_readonly_user" {
  source = "path/to/module"
  
  region = "your-AWS-region"
  cluster_endpoint = "your-docdb-cluster.region.docdb.amazonaws.com"
  admin_secret_arn = "arn:aws:secretsmanager:region:account:secret:admin-credentials"
  
  username = "readonlyuser"
  roles = [
    {
      role = "read"
      db   = "myapp"
    }
  ]
}
```

## Input Variables

| Name | Description | Type | Required | Default |
|------|-------------|------|----------|---------|
| `region` | AWS region where you resources re deployed | `string` | Yes | `us-east-1` |
| `cluster_endpoint` | Amazon DocumentDB cluster endpoint (hostname without protocol or port) | `string` | Yes | - |
| `admin_secret_arn` | AWS Secrets Manager ARN containing master credentials | `string` | Yes | - |
| `username` | Username to manage (3-63 chars, must start with letter, alphanumeric with underscores) | `string` | Yes | - |
| `roles` | List of roles for the user | `list(object)` | Yes | - |
| `cluster_port` | Amazon DocumentDB port | `string` | No | `"27017"` |

### Role Format

Each role in the `roles` list should have the following format:

```hcl
{
  role = "readWrite"  # The role name (e.g., read, readWrite, dbAdmin)
  db   = "myapp"      # The database name to apply the role to
}
```

## Additional Details

### Admin Secret Format
The admin secret in AWS Secrets Manager should have the following format:
```json
{
  "username": "admin",
  "password": "your-admin-password"
}
```

### User Management
The module automatically:
1. Creates a new AWS Secrets Manager secret named `${username}-docdb-credentials`
2. Generates a secure random password for the user
3. Stores the username and password in the secret

The user secret will have the following format:
```json
{
  "username": "your-username",
  "password": "auto-generated-secure-password"
}
```

## Examples

### Read-Only User
```hcl
module "docdb_readonly_user" {
  source = "./users"
  
  region = "your-AWS-region"
  cluster_endpoint = "your-docdb-cluster.region.docdb.amazonaws.com"
  admin_secret_arn = "arn:aws:secretsmanager:region:account:secret:admin-credentials"
  
  username = "readonlyuser"
  roles = [
    {
      role = "read"
      db   = "myapp"
    }
  ]
}
```

### Power User with Multiple Roles
```hcl
module "docdb_admin_user" {
  source = "./users"
  
  region = "your-AWS-region"
  cluster_endpoint = "your-docdb-cluster.region.docdb.amazonaws.com"
  admin_secret_arn = "arn:aws:secretsmanager:region:account:secret:admin-credentials"
  
  username = "adminuser"
  roles = [
    {
      role = "readWrite"
      db   = "myapp1"
    },
    {
      role = "dbAdmin"
      db   = "myapp2"
    }
  ]
}
```

## Notes

- The module uses the `mongosh` client to interact with Amazon DocumentDB
- Currently only supports clusters with [SSL/TLS](https://docs.aws.amazon.com/documentdb/latest/developerguide/security.encryption.ssl.html) enabled (default configuration)
- Automatically downloads the required certificate bundle (`global-bundle.pem`)
- This relies on AWS Secret Manager to handle password updates and rotation (see the [AWS Secrets Manager Developer Guide](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html) for more details)
- Changes to roles will trigger user updates
- Username validation ensures compliance with [Amazon DocumentDB naming requirements](https://docs.aws.amazon.com/documentdb/latest/developerguide/limits.html#limits-naming_constraints)
