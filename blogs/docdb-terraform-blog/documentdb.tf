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

  # Allowed values: disabled, enabled, fips-140-3, tls1.2+, tls1.3+
  # "enabled" permits TLS 1.0-1.3; "tls1.2+" enforces TLS 1.2 or higher.
  parameter {
    name  = "tls"
    value = "tls1.2+"
  }

  # Allowed values: enabled, disabled, ddl, dml_read, dml_write, all, none
  # "enabled" is a legacy alias that audits DDL only. "ddl,dml_write" also
  # captures data modifications for compliance without the volume of "dml_read"
  # (every read). Use "all" for maximum fidelity at higher log volume and cost.
  parameter {
    name  = "audit_logs"
    value = "ddl,dml_write"
  }

  parameter {
    name  = "profiler"
    value = "enabled"
  }

  # Log operations slower than this threshold (allowed: 50-2147483646 ms).
  parameter {
    name  = "profiler_threshold_ms"
    value = "100"
  }

  # Fraction of qualifying operations to log (allowed: 0.0-1.0). Set explicitly
  # so the volume is intentional. Profiler logs capture query content, so lower
  # this in sensitive or high-traffic environments to reduce exposure and cost.
  parameter {
    name  = "profiler_sampling_rate"
    value = "1.0"
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

  # Instances have auto_minor_version_upgrade enabled, so DocumentDB may apply
  # minor patches during the maintenance window. Ignore engine_version drift so
  # those auto-applied upgrades do not cause plan churn or get reverted on apply.
  lifecycle {
    ignore_changes = [engine_version]
  }
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

  # Apply minor engine patches automatically during the maintenance window.
  auto_minor_version_upgrade = true

  tags = merge(var.tags, { "Name" = "${var.name}-instance-${count.index}" })
}
