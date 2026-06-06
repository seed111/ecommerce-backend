variable "cluster_name" {
  type = string
}

variable "cluster_version" {
  type    = string
  default = "1.32"
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "public_access_cidrs" {
  type    = list(string)
  default = ["0.0.0.0/0"]
}

variable "node_instance_types" {
  type    = list(string)
  default = ["t3.medium"]
}

variable "node_capacity_type" {
  type    = string
  default = "ON_DEMAND"
}

variable "node_desired" {
  type    = number
  default = 2
}

variable "node_min" {
  type    = number
  default = 1
}

variable "node_max" {
  type    = number
  default = 4
}

variable "app_namespace" {
  type    = string
  default = "ecommerce"
}

variable "app_service_account" {
  type    = string
  default = "ecommerce-api"
}

variable "dynamodb_table_arns" {
  type = list(string)
}

variable "s3_bucket_arn" {
  type = string
}

variable "secret_arns" {
  type = list(string)
}

variable "tags" {
  type    = map(string)
  default = {}
}