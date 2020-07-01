resource "aws_glue_catalog_database" "analytical_dataset_generation" {
  name        = "analytical_dataset_generation"
  description = "Database for the Analytical Dataset"
}

output "analytical_dataset_generation" {
  value = {
    job_name = aws_glue_catalog_database.analytical_dataset_generation.name
  }
}

resource "aws_glue_catalog_database" "analytical_dataset_generation_staging" {
  name        = "analytical_dataset_generation_staging"
  description = "Staging Database for analytical dataset generation"
}

output "analytical_dataset_generation_staging" {
  value = {
    job_name = aws_glue_catalog_database.analytical_dataset_generation_staging.name
  }
}

data "aws_iam_policy_document" "analytical_dataset_generator_gluetables_write" {
  statement {
    effect = "Allow"

    actions = [
      "glue:CreateTable",
      "glue:DeleteTable",
    ]

    resources = [
      "arn:aws:glue:${var.region}:${local.account[local.environment]}:database/${aws_glue_catalog_database.analytical_dataset_generation_staging.name}",
      "arn:aws:glue:${var.region}:${local.account[local.environment]}:database/${aws_glue_catalog_database.analytical_dataset_generation.name}",
      "arn:aws:glue:${var.region}:${local.account[local.environment]}:catalog",
    ]
  }
}

resource "aws_iam_policy" "analytical_dataset_generator_gluetables_write" {
  name        = "AnalyticalDatasetGeneratorGlueTablesWrite"
  description = "Allow creation and deletion of ADG Glue tables"
  policy      = data.aws_iam_policy_document.analytical_dataset_generator_gluetables_write.json
}
