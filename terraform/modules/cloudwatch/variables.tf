variable "env" {
  type = string
}

variable "cluster_name" {
  type = string
}

variable "lambda_function_name" {
  type = string
}

variable "log_retention_days" {
  type    = number
  default = 14
}

variable "alarm_sns_arn" {
  type    = string
  default = ""
}

variable "tags" {
  type    = map(string)
  default = {}
}