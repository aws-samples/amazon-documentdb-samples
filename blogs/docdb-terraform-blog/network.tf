module "vpc" {
  source = "./network"

  region              = var.region
  vpc_name            = var.name
  vpc_cidr            = var.vpc_cidr
  subnet_cidr_private = var.subnet_cidr_private
  tags                = var.tags
}
