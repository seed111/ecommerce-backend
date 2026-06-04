resource "aws_cloudwatch_log_group" "eks_app" {
  name              = "/aws/eks/${var.cluster_name}/application"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_eks_addon" "cloudwatch_observability" {
  cluster_name                = var.cluster_name
  addon_name                  = "amazon-cloudwatch-observability"
  resolve_conflicts_on_update = "OVERWRITE"
  tags                        = var.tags
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.env}-order-processor-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 5
  treat_missing_data  = "notBreaching"

  dimensions    = { FunctionName = var.lambda_function_name }
  alarm_actions = var.alarm_sns_arn != "" ? [var.alarm_sns_arn] : []
  tags          = var.tags
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "${var.env}-order-processor-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "p95"
  threshold           = 25000
  treat_missing_data  = "notBreaching"

  dimensions    = { FunctionName = var.lambda_function_name }
  alarm_actions = var.alarm_sns_arn != "" ? [var.alarm_sns_arn] : []
  tags          = var.tags
}

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.env}-ecommerce"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          title  = "Lambda Invocations & Errors"
          period = 60
          stat   = "Sum"
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", var.lambda_function_name],
            ["AWS/Lambda", "Errors", "FunctionName", var.lambda_function_name],
          ]
        }
      },
      {
        type = "metric"
        properties = {
          title   = "Lambda Duration p95"
          period  = 60
          stat    = "p95"
          metrics = [["AWS/Lambda", "Duration", "FunctionName", var.lambda_function_name]]
        }
      }
    ]
  })
}