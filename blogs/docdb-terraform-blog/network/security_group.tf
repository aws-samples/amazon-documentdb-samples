#https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/default_security_group
# Disable the default security group to enforce explicit security group usage
resource "aws_default_security_group" "default" {
  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, { "Name" = "${var.vpc_name}-default-sg-restricted" })
}

#https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/security_group
# Custom security group for DocumentDB access
resource "aws_security_group" "docdb" {
  name        = "${var.vpc_name}_allow_docdb_access"
  description = "Security group for DocumentDB cluster access"
  vpc_id      = aws_vpc.this.id

  tags = merge(var.tags, { "Name" = "${var.vpc_name}-docdb-sg" })
}

#https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_security_group_ingress_rule
resource "aws_vpc_security_group_ingress_rule" "docdb_ingress" {
  security_group_id = aws_security_group.docdb.id
  description       = "Allow DocumentDB traffic from within VPC"
  from_port         = 27017
  to_port           = 27017
  ip_protocol       = "tcp"
  cidr_ipv4         = var.vpc_cidr
}

#https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_security_group_egress_rule
resource "aws_vpc_security_group_egress_rule" "docdb_egress" {
  security_group_id = aws_security_group.docdb.id
  description       = "Allow outbound traffic within VPC"
  ip_protocol       = "-1"
  cidr_ipv4         = var.vpc_cidr
}
