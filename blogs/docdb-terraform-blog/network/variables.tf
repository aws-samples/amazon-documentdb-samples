variable "region" {
  description = "AWS region for deployment"
  type        = string

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]{1}$", var.region))
    error_message = "Region must be a valid AWS region format (e.g., us-east-1)."
  }
}

variable "vpc_name" {
  description = "Name prefix for VPC and related resources"
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9-]+$", var.vpc_name))
    error_message = "VPC name must contain only alphanumeric characters and hyphens."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR must be a valid IPv4 CIDR block."
  }
}

variable "subnet_cidr_private" {
  description = "List of CIDR blocks for private subnets"
  type        = list(string)

  validation {
    condition     = length(var.subnet_cidr_private) >= 2
    error_message = "At least two private subnet CIDRs are required for multi-AZ deployment."
  }
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
