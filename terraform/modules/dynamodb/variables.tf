variable "env" {
  type = string
}

variable "enable_pitr" {
  type    = bool
  default = true
}

variable "tags" {
  type    = map(string)
  default = {}
}