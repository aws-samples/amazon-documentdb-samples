terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# Retrieve primary user credentials from AWS Secrets Manager
data "aws_secretsmanager_secret_version" "primary" {
  secret_id = var.admin_secret_arn
}

# Saved user secret name
resource "aws_secretsmanager_secret" "user_secret" {
  name = "${var.username}-docdb-credentials"
}

# Create complex password
resource "random_password" "initial_password" {
  length           = 32
  special         = true
  lower           = true
  upper           = true
  numeric         = true
  min_lower       = 1
  min_upper       = 1
  min_numeric     = 1
  min_special     = 1
  override_special = "!#$%&*()-_=+[]{}<>:?"  
}

resource "aws_secretsmanager_secret_version" "user_credentials" {
  secret_id = aws_secretsmanager_secret.user_secret.id
  secret_string = jsonencode({
    username = var.username
    password = random_password.initial_password.result
  })
}

locals {
  # Parse credentials from Secrets Manager
  primary_credentials = jsondecode(data.aws_secretsmanager_secret_version.primary.secret_string)
  primary_username   = local.primary_credentials["username"]
  primary_password   = local.primary_credentials["password"]
}

# Call upon scripts to create, update role, and delete users
resource "null_resource" "manage_user" {
  triggers = {
    username       = var.username
    docdb_user     = local.primary_username
    docdb_password = local.primary_password
    docdb_host     = var.cluster_endpoint
    docdb_port     = var.cluster_port
    roles_hash     = sha256(jsonencode(var.roles))
  }

  depends_on = [null_resource.download_cert]

  # Create user or update their role
  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    environment = {
      DOCDB_USER     = local.primary_username
      DOCDB_PASSWORD = local.primary_password
      DOCDB_HOST     = var.cluster_endpoint
      DOCDB_PORT     = var.cluster_port
      USERNAME       = var.username
      USER_PASSWORD  = random_password.initial_password.result
      ROLES          = jsonencode(var.roles)
      ACTION         = "create"
      OPERATION_ID   = uuid()
    }
    command = file("${path.module}/scripts/manage_docdb_user.sh")
  }

  # Delete user on destroy
  provisioner "local-exec" {
    when        = destroy
    interpreter = ["/bin/bash", "-c"]
    environment = {
      DOCDB_USER     = self.triggers.docdb_user
      DOCDB_PASSWORD = self.triggers.docdb_password
      DOCDB_HOST     = self.triggers.docdb_host
      DOCDB_PORT     = self.triggers.docdb_port
      USERNAME       = self.triggers.username
      ACTION         = "delete"
      OPERATION_ID   = uuid()
    }
    command = file("${path.module}/scripts/manage_docdb_user.sh")
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Download DocumentDB TLS pem
resource "null_resource" "download_cert" {
  provisioner "local-exec" {
    command = file("${path.module}/scripts/download_cert.sh")
  }
}

# Output information about the user
output "user_info" {
  description = "Information about the Amazon DocumentDB user"
  value = {
    username    = var.username
    roles       = var.roles
    endpoint    = var.cluster_endpoint
    created_at  = timestamp()
  }
  sensitive = true
}