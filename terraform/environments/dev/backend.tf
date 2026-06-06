terraform {
  backend "s3" {
    bucket       = "ecommerce-terraform-state-dev-seed111"
    key          = "dev/terraform.tfstate"
    region       = "eu-west-1"
    use_lockfile = true
    encrypt      = true
  }
}
