variable "region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]{1}$", var.region))
    error_message = "Region must be a valid AWS region format (e.g., us-east-1)."
  }
}

variable "name" {
  description = "Name prefix for all resources"
  type        = string
  default     = "docdb-terraform-demo"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]*$", var.name))
    error_message = "Name must start with a lowercase letter and contain only lowercase alphanumeric characters and hyphens."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR must be a valid IPv4 CIDR block."
  }
}

variable "subnet_cidr_private" {
  description = "List of CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]

  validation {
    condition     = length(var.subnet_cidr_private) >= 2
    error_message = "At least two private subnet CIDRs are required for multi-AZ deployment."
  }
}

variable "engine_version" {
  description = "DocumentDB engine version"
  type        = string
  default     = "8.0.1"
}

variable "instance_class" {
  description = "Instance class for DocumentDB instances"
  type        = string
  default     = "db.t4g.medium"
}

variable "instance_count" {
  description = "Number of DocumentDB instances in the cluster"
  type        = number
  default     = 2

  validation {
    condition     = var.instance_count >= 1 && var.instance_count <= 16
    error_message = "Instance count must be between 1 and 16."
  }
}

variable "master_username" {
  description = "Master username for the DocumentDB cluster"
  type        = string
  default     = "docdbadmin"

  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9]*$", var.master_username))
    error_message = "Master username must start with a letter and contain only alphanumeric characters."
  }
}

variable "backup_retention_period" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7

  validation {
    condition     = var.backup_retention_period >= 1 && var.backup_retention_period <= 35
    error_message = "Backup retention period must be between 1 and 35 days."
  }
}

variable "preferred_backup_window" {
  description = "Daily time range for automated backups (UTC)"
  type        = string
  default     = "03:00-04:00"
}

variable "preferred_maintenance_window" {
  description = "Weekly time range for system maintenance (UTC)"
  type        = string
  default     = "sun:04:00-sun:05:00"
}

variable "deletion_protection" {
  description = "Enable deletion protection for the cluster"
  type        = bool
  default     = true
}

variable "skip_final_snapshot" {
  description = "Skip final snapshot when deleting the cluster"
  type        = bool
  default     = false
}

variable "enable_performance_insights" {
  description = "Enable Performance Insights for cluster instances"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
