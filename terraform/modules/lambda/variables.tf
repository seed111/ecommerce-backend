variable "env" {
  type = string
}

variable "orders_stream_arn" {
  type = string
}

variable "orders_table_arn" {
  type = string
}

variable "products_table_arn" {
  type = string
}

variable "orders_table_name" {
  type = string
}

variable "products_table_name" {
  type = string
}

variable "log_retention_days" {
  type    = number
  default = 14
}

variable "tags" {
  type    = map(string)
  default = {}
}