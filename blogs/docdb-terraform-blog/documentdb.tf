#https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/docdb_subnet_group
resource "aws_docdb_subnet_group" "this" {
  name       = "${var.name}-subnet-group"
  subnet_ids = module.vpc.private_subnets[*].id

  tags = merge(var.tags, { "Name" = "${var.name}-subnet-group" })
}

#https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/docdb_cluster_parameter_group
resource "aws_docdb_cluster_parameter_group" "this" {
  family      = "docdb8.0"
  name        = "${var.name}-params"
  description = "DocumentDB 8.0 cluster parameter group with security settings"

  parameter {
    name  = "tls"
    value = "enabled"
  }

  parameter {
    name  = "audit_logs"
    value = "enabled"
  }

  parameter {
    name  = "profiler"
    value = "enabled"
  }

  tags = merge(var.tags, { "Name" = "${var.name}-params" })
}

#https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/docdb_cluster
resource "aws_docdb_cluster" "this" {
  cluster_identifier = var.name
  engine             = "docdb"
  engine_version     = var.engine_version
  port               = 27017

  # Authentication - AWS Secrets Manager managed password
  master_username             = var.master_username
  manage_master_user_password = true

  # Encryption at rest
  storage_encrypted = true
  kms_key_id        = aws_kms_key.docdb.arn

  # Network
  vpc_security_group_ids = [module.vpc.security_group.id]
  db_subnet_group_name   = aws_docdb_subnet_group.this.name

  # Parameter group
  db_cluster_parameter_group_name = aws_docdb_cluster_parameter_group.this.name

  # Backup
  backup_retention_period      = var.backup_retention_period
  preferred_backup_window      = var.preferred_backup_window
  preferred_maintenance_window = var.preferred_maintenance_window

  # Logging
  enabled_cloudwatch_logs_exports = ["audit", "profiler"]

  # Protection
  deletion_protection       = var.deletion_protection
  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${var.name}-final-snapshot"

  tags = merge(var.tags, { "Name" = var.name })

  depends_on = [
    aws_cloudwatch_log_group.audit,
    aws_cloudwatch_log_group.profiler
  ]
}

#https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/docdb_cluster_instance
resource "aws_docdb_cluster_instance" "this" {
  count              = var.instance_count
  identifier         = "${var.name}-${count.index}"
  cluster_identifier = aws_docdb_cluster.this.id
  instance_class     = var.instance_class

  # Performance Insights
  enable_performance_insights     = var.enable_performance_insights
  performance_insights_kms_key_id = var.enable_performance_insights ? aws_kms_key.docdb.arn : null

  tags = merge(var.tags, { "Name" = "${var.name}-instance-${count.index}" })
}
