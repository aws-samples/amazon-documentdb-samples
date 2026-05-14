output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.this.id
}

output "private_subnets" {
  description = "List of private subnet objects"
  value       = aws_subnet.private
}

output "security_group" {
  description = "DocumentDB security group"
  value       = aws_security_group.docdb
}
