terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.tags
  }
}

data "aws_caller_identity" "current" {}

locals {
  env          = "dev"
  cluster_name = "${local.env}-ecommerce-eks"

  tags = {
    Environment = local.env
    Project     = "ecommerce-backend"
    ManagedBy   = "terraform"
  }
}

module "networking" {
  source       = "../../modules/networking"
  name         = "${local.env}-ecommerce"
  cluster_name = local.cluster_name
  vpc_cidr     = var.vpc_cidr
  tags         = local.tags
}

module "ecr" {
  source = "../../modules/ecr"
  env    = local.env
  tags   = local.tags
}

module "s3" {
  source     = "../../modules/s3"
  env        = local.env
  account_id = data.aws_caller_identity.current.account_id
  tags       = local.tags
}

module "dynamodb" {
  source      = "../../modules/dynamodb"
  env         = local.env
  enable_pitr = false
  tags        = local.tags
}

module "secrets" {
  source = "../../modules/secrets"
  env    = local.env
  tags   = local.tags
}

module "eks" {
  source              = "../../modules/eks"
  cluster_name        = local.cluster_name
  cluster_version     = var.eks_cluster_version
  private_subnet_ids  = module.networking.private_subnet_ids
  node_instance_types = var.node_instance_types
  node_capacity_type  = "ON_DEMAND"
  node_desired        = 2
  node_min            = 1
  node_max            = 3
  dynamodb_table_arns = module.dynamodb.table_arns
  s3_bucket_arn       = module.s3.bucket_arn
  secret_arns         = [module.secrets.secret_arn]
  tags                = local.tags
}

module "lambda" {
  source              = "../../modules/lambda"
  env                 = local.env
  orders_stream_arn   = module.dynamodb.orders_stream_arn
  orders_table_arn    = module.dynamodb.table_arns[1]
  products_table_arn  = module.dynamodb.table_arns[0]
  orders_table_name   = module.dynamodb.orders_table_name
  products_table_name = module.dynamodb.products_table_name
  log_retention_days  = 7
  tags                = local.tags
}

module "cloudwatch" {
  source               = "../../modules/cloudwatch"
  env                  = local.env
  cluster_name         = local.cluster_name
  lambda_function_name = module.lambda.function_name
  log_retention_days   = 7
  alarm_sns_arn        = ""
  tags                 = local.tags
  depends_on           = [module.eks]
}