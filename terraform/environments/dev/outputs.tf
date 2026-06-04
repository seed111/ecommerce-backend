output "cluster_name" {
  value = module.eks.cluster_name
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "ecr_repository_url" {
  value = module.ecr.repository_url
}

output "app_irsa_role_arn" {
  value = module.eks.app_irsa_role_arn
}

output "s3_bucket_name" {
  value = module.s3.bucket_name
}

output "products_table_name" {
  value = module.dynamodb.products_table_name
}

output "orders_table_name" {
  value = module.dynamodb.orders_table_name
}

output "users_table_name" {
  value = module.dynamodb.users_table_name
}

output "secret_name" {
  value = module.secrets.secret_name
}