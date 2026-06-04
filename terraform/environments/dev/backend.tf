terraform {
  backend "s3" {
    bucket         = "ecommerce-terraform-state-dev"
    key            = "dev/terraform.tfstate"
    region         = "eu-west-1"
    dynamodb_table = "ecommerce-terraform-locks"
    encrypt        = true
  }
}