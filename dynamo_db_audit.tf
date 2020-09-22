resource "aws_dynamodb_table" "data_pipeline_metadata123" {
  name         = "data_pipeline_metadata123"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "RunId"
  range_key    = "Correlation_Id"

  attribute {
    name = "RunId"
    type = "S"
  }

  attribute {
    name = "Correlation_Id"
    type = "S"
  }

  tags = merge(
    local.common_tags,
    map("Name", "data_pipeline_metadata_dynamo")
  )

}

output "data_pipeline_metadata_dynamo" {
  value = aws_dynamodb_table.data_pipeline_metadata123
}