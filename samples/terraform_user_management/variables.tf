# users/variables.tf
variable "region" {
  type        = string
  description = "AWS region"
  default     = "us-east-1"
}

variable "cluster_endpoint" {
  type = string
  description = "DocumentDB cluster endpoint. Example - sample-cluster.cluster-sfcrlcjcoroz.us-east-1.docdb.amazonaws.com"
}

variable "cluster_port" {
  type = string
  description = "DocumentDB port (default 27017)"
  default = "27017"
}

variable "admin_secret_arn" {
  description = "The ARN of the secret containing primary user's credentials"
  type        = string
  
  validation {
    condition     = can(regex("^arn:aws:secretsmanager:", var.admin_secret_arn))
    error_message = "The admin_secret_arn must be a valid Secret Manager ARN."
  }
}

variable "username" {
  type = string
  description = "Username to manage"
  validation {
    condition     = length(var.username) >= 3 && length(var.username) <= 63 && can(regex("^[a-zA-Z][a-zA-Z0-9_]*$", var.username))
    error_message = "Username must be 3-63 characters, start with a letter, and contain only letters, numbers, and underscores."
  }
}

variable "roles" {
  type = list(object({
    role = string
    db   = string
  }))
  description = <<-EOT
    List of role objects containing role and database assignments.
    Example:
      roles = [
        {
          role = "read"
          db   = "sample-database-1"
        },
        {
          role = "readWrite"
          db   = "database2"
        }
      ]
  EOT
  validation {
    condition     = length(var.roles) > 0
    error_message = "At least one role must be specified."
  }
}