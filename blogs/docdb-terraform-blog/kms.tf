#https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/caller_identity
data "aws_caller_identity" "current" {}

locals {
  principal_root_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
}

#https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kms_key
resource "aws_kms_key" "docdb" {
  description             = "KMS key for DocumentDB encryption - ${var.name}"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(var.tags, { "Name" = "${var.name}-docdb-kms" })
}

#https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kms_key_policy
resource "aws_kms_key_policy" "docdb" {
  key_id = aws_kms_key.docdb.id
  policy = jsonencode({
    Id = "${var.name}-docdb-key-policy"
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
        Sid    = "Allow DocumentDB Service"
        Effect = "Allow"
        Principal = {
          Service = "rds.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:CreateGrant",
          "kms:ReEncrypt*",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "rds.${var.region}.amazonaws.com"
          }
        }
      }
    ]
    Version = "2012-10-17"
  })
}

#https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kms_alias
resource "aws_kms_alias" "docdb" {
  name          = "alias/${var.name}-docdb"
  target_key_id = aws_kms_key.docdb.key_id
}
