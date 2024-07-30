terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.8"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

provider "archive" {}

data "archive_file" "stopzip" {
  type        = "zip"
  source_file = "AutoStopCluster.py"
  output_path = "AutoStopCluster.zip"
}

data "archive_file" "startzip" {
  type        = "zip"
  source_file = "AutoStartCluster.py"
  output_path = "AutoStartCluster.zip"
}

resource "aws_iam_role" "docdbLambdaRole" {
  name = "docdbLambdaRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

data "aws_iam_policy_document" "docdbLambdaPolicyDoc" {

  statement {
    actions = [
      "rds:StartDBCluster",
      "rds:StopDBCluster",
      "rds:DescribeDBClusters",
      "rds:ListTagsForResource",
      "logs:CreateLogStream",
      "logs:CreateLogGroup",
      "logs:PutLogEvents"
    ]

    resources = [
      "arn:aws:rds:${var.aws_region}:${var.aws_account_id}:cluster:*",
      "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:*"
    ]
  }
}

resource "aws_iam_policy" "docdbLambdaPolicy" {
  name        = "DocDB_LambdaPolicy"
  path        = "/"
  description = "Allows Lambda to AutoStop and AutoStart tagged DocDB clusters"
  policy      = data.aws_iam_policy_document.docdbLambdaPolicyDoc.json
}

resource "aws_iam_role_policy_attachment" "docdbLambdaPolicy" {
  role       = aws_iam_role.docdbLambdaRole.name
  policy_arn = aws_iam_policy.docdbLambdaPolicy.arn
}

resource "aws_lambda_function" "DocDBStopCluster" {
  function_name    = "DocDBStopCluster1"
  filename         = data.archive_file.stopzip.output_path
  source_code_hash = data.archive_file.stopzip.output_base64sha256
  role             = aws_iam_role.docdbLambdaRole.arn
  handler          = "AutoStopCluster.lambda_handler"
  runtime          = "python3.9"
  timeout          = 60
}

resource "aws_lambda_function" "DocDBStartCluster" {
  function_name    = "DocDBStartCluster1"
  filename         = data.archive_file.startzip.output_path
  source_code_hash = data.archive_file.startzip.output_base64sha256
  role             = aws_iam_role.docdbLambdaRole.arn
  handler          = "AutoStartCluster.lambda_handler"
  runtime          = "python3.9"
  timeout          = 60
}

module "DocDB_AutoStop_EB" {
  source               = "terraform-aws-modules/eventbridge/aws"
  version              = "2.3.0"
  create_bus           = false
  attach_lambda_policy = true
  role_name            = "DocDB_EB_Scheduler_AutoStop"
  lambda_target_arns   = [aws_lambda_function.DocDBStopCluster.arn]
  schedules = {
    DocDB_AutoStop_EB = {
      description         = "Auto stop DocDB clusters with AutoStop tag"
      schedule_expression = "cron(30 17 ? * MON-FRI *)"
      timezone            = "America/Chicago"
      arn                 = aws_lambda_function.DocDBStopCluster.arn
    }
  }
}

module "DocDB_AutoStart_EB" {
  source               = "terraform-aws-modules/eventbridge/aws"
  version              = "2.3.0"
  create_bus           = false
  attach_lambda_policy = true
  role_name            = "DocDB_EB_Scheduler_AutoStart"
  lambda_target_arns   = [aws_lambda_function.DocDBStartCluster.arn]
  schedules = {
    DocDB_AutoStart_EB = {
      description         = "Auto start DocDB clusters with AutoStart tag"
      schedule_expression = "cron(0 8 ? * MON-FRI *)"
      timezone            = "America/Chicago"
      arn                 = aws_lambda_function.DocDBStartCluster.arn
    }
  }
}