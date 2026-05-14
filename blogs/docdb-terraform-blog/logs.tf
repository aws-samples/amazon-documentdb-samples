#https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kms_key
# KMS key for encrypting CloudWatch log groups
resource "aws_kms_key" "logs" {
  description             = "KMS key for DocumentDB CloudWatch logs - ${var.name}"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(var.tags, { "Name" = "${var.name}-logs-kms" })
}

#https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kms_key_policy
resource "aws_kms_key_policy" "logs" {
  key_id = aws_kms_key.logs.id
  policy = jsonencode({
    Id = "${var.name}-logs-key-policy"
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
        Sid    = "Allow CloudWatch Logs Service"
        Effect = "Allow"
        Principal = {
          Service = "logs.${var.region}.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          ArnEquals = {
            "kms:EncryptionContext:aws:logs:arn" = [
              "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/docdb/${var.name}/audit",
              "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/docdb/${var.name}/profiler"
            ]
          }
        }
      }
    ]
    Version = "2012-10-17"
  })
}

#https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kms_alias
resource "aws_kms_alias" "logs" {
  name          = "alias/${var.name}-logs"
  target_key_id = aws_kms_key.logs.key_id
}

#https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_group
# CloudWatch log groups for DocumentDB audit and profiler logs
resource "aws_cloudwatch_log_group" "audit" {
  name              = "/aws/docdb/${var.name}/audit"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.logs.arn

  tags = merge(var.tags, { "Name" = "${var.name}-audit-logs" })

  depends_on = [aws_kms_key_policy.logs]
}

#https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_group
resource "aws_cloudwatch_log_group" "profiler" {
  name              = "/aws/docdb/${var.name}/profiler"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.logs.arn

  tags = merge(var.tags, { "Name" = "${var.name}-profiler-logs" })

  depends_on = [aws_kms_key_policy.logs]
}
