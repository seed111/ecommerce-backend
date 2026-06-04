output "products_table_name" { value = aws_dynamodb_table.products.name }
output "orders_table_name" { value = aws_dynamodb_table.orders.name }
output "users_table_name" { value = aws_dynamodb_table.users.name }
output "orders_stream_arn" { value = aws_dynamodb_table.orders.stream_arn }
output "table_arns" {
  value = [
    aws_dynamodb_table.products.arn,
    aws_dynamodb_table.orders.arn,
    aws_dynamodb_table.users.arn,
  ]
}