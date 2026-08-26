output "cluster_endpoint" {
  description = "DocumentDB cluster endpoint for write operations"
  value       = aws_docdb_cluster.this.endpoint
}

output "cluster_reader_endpoint" {
  description = "DocumentDB cluster reader endpoint for read operations"
  value       = aws_docdb_cluster.this.reader_endpoint
}

output "cluster_port" {
  description = "Port the DocumentDB cluster is listening on"
  value       = aws_docdb_cluster.this.port
}

output "cluster_arn" {
  description = "ARN of the DocumentDB cluster"
  value       = aws_docdb_cluster.this.arn
}

output "master_user_secret_arn" {
  description = "ARN of the master user secret in AWS Secrets Manager"
  value       = aws_docdb_cluster.this.master_user_secret[0].secret_arn
  sensitive   = true
}

output "kms_key_arn" {
  description = "ARN of the KMS key used for DocumentDB encryption"
  value       = aws_kms_key.docdb.arn
}

output "vpc_id" {
  description = "ID of the VPC where DocumentDB is deployed"
  value       = module.vpc.vpc_id
}

output "security_group_id" {
  description = "ID of the security group attached to DocumentDB"
  value       = module.vpc.security_group.id
}
