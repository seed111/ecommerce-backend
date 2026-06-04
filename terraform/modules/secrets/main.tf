resource "aws_secretsmanager_secret" "app" {
  name                    = "${var.env}/ecommerce/app"
  description             = "Application secrets for ${var.env} ecommerce backend"
  recovery_window_in_days = var.env == "prod" ? 30 : 0
  tags                    = var.tags
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    jwt_secret     = "REPLACE_ME"
    stripe_api_key = "REPLACE_ME"
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}