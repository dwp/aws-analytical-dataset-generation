resource "aws_s3_bucket_object" "generate-analytical-dataset-script" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  key        = "component/analytical-dataset-generation/generate-analytical-dataset.py"
  content    = data.template_file.analytical_dataset_generation_script.rendered
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
}

data "template_file" "analytical_dataset_generation_script" {
  template = file(format("%s/generate-analytical-dataset.py", path.module))
  vars = {
  }
}

resource "aws_s3_bucket_object" "analytical_dataset_generator_cluster_payload" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  key        = "component/analytical-dataset-generation/analytical-dataset-generator-cluster-payload.json"
  content    = data.template_file.analytical_dataset_generator_cluster_payload.rendered
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
}

data "template_file" "analytical_dataset_generator_cluster_payload" {
  template = file(format("%s/payload.json", path.module))
  vars = {
  }
}
