resource "aws_glue_catalog_database" "analytical_dataset_generation" {
  name        = "analytical_dataset_generation"
  description = "Database for the Manifest comparision ETL"
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
