#https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kms_key
resource "aws_kms_key" "ssm" {
  description             = "KMS key for SSM Parameter Store - ${var.name}"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(var.tags, { "Name" = "${var.name}-ssm-kms" })
}

#https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kms_key_policy
resource "aws_kms_key_policy" "ssm" {
  key_id = aws_kms_key.ssm.id
  policy = jsonencode({
    Id = "${var.name}-ssm-key-policy"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = local.principal_root_arn
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow SSM Service"
        Effect = "Allow"
        Principal = {
          Service = "ssm.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "ssm.${var.region}.amazonaws.com"
          }
        }
      }
    ]
    Version = "2012-10-17"
  })
}

#https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kms_alias
resource "aws_kms_alias" "ssm" {
  name          = "alias/${var.name}-ssm"
  target_key_id = aws_kms_key.ssm.key_id
}

#https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_parameter
resource "aws_ssm_parameter" "docdb_output" {
  name        = "/${var.name}/output"
  description = "DocumentDB cluster infrastructure outputs."
  type        = "SecureString"
  key_id      = aws_kms_key.ssm.id
  value = jsonencode({
    "cluster_endpoint"        : aws_docdb_cluster.this.endpoint,
    "cluster_reader_endpoint" : aws_docdb_cluster.this.reader_endpoint,
    "cluster_port"            : tostring(aws_docdb_cluster.this.port),
    "cluster_arn"             : aws_docdb_cluster.this.arn,
    "master_user_secret_arn"  : aws_docdb_cluster.this.master_user_secret[0].secret_arn,
    "kms_key_arn"             : aws_kms_key.docdb.arn,
    "security_group_id"       : module.vpc.security_group.id,
    "vpc_id"                  : module.vpc.vpc_id
  })

  tags = merge(var.tags, { "Name" = "${var.name}-output" })
}
