resource "aws_iam_role" "lambda" {
  name = "${var.env}-order-processor-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda" {
  name = "${var.env}-order-processor-policy"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DynamoDBStreams"
        Effect = "Allow"
        Action = [
          "dynamodb:GetRecords", "dynamodb:GetShardIterator",
          "dynamodb:DescribeStream", "dynamodb:ListStreams",
        ]
        Resource = [var.orders_stream_arn]
      },
      {
        Sid      = "DynamoDBWrite"
        Effect   = "Allow"
        Action   = ["dynamodb:UpdateItem", "dynamodb:GetItem"]
        Resource = [var.orders_table_arn, var.products_table_arn]
      },
      {
        Sid      = "CloudWatch"
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

data "archive_file" "order_processor" {
  type        = "zip"
  source_dir  = "${path.root}/../../lambda/order_processor"
  output_path = "${path.module}/order_processor.zip"
}

resource "aws_lambda_function" "order_processor" {
  function_name    = "${var.env}-order-processor"
  role             = aws_iam_role.lambda.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  filename         = data.archive_file.order_processor.output_path
  source_code_hash = data.archive_file.order_processor.output_base64sha256
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      ENV                 = var.env
      PRODUCTS_TABLE_NAME = var.products_table_name
      ORDERS_TABLE_NAME   = var.orders_table_name
    }
  }

  logging_config {
    log_format = "JSON"
    log_group  = aws_cloudwatch_log_group.lambda.name
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
    aws_cloudwatch_log_group.lambda,
  ]

  tags = var.tags
}

resource "aws_lambda_event_source_mapping" "orders_stream" {
  event_source_arn  = var.orders_stream_arn
  function_name     = aws_lambda_function.order_processor.arn
  starting_position = "LATEST"
  batch_size        = 10

  filter_criteria {
    filter {
      pattern = jsonencode({ eventName = ["INSERT"] })
    }
  }
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.env}-order-processor"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}