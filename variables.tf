variable "emr_release_label" {
  description = "Version of AWS EMR to deploy with associated applicatoins"
  default     = "emr-5.24.1"
}

variable "emr_applications" {
  description = "List of applications to deploy to EMR Cluster"
  type        = list(string)
  default     = ["Spark", "HBase", "Hive"]
}

variable "termination_protection" {
  description = "Default setting for Termination Protection"
  type        = bool
  default     = false
}

variable "keep_flow_alive" {
  description = "Indicates whether to keep job flow alive when no active steps"
  type        = bool
  default     = true //TODO set this to false when you want the cluster to autoterminate when final step completes
}

variable "truststore_aliases" {
  description = "comma seperated truststore aliases"
  type        = list(string)
  default     = ["dataworks_root_ca", "dataworks_mgt_root_ca", "ca_cert", "mgmt_cert", "root_ca"]
}

variable "truststore_certs" {
  description = "comma seperated truststore certificates"
  type        = list(string)
  default     = [
    "s3://${local.env_certificate_bucket}/ca_certificates/dataworks/dataworks_root_ca.pem",
    "s3://dw-management-dev-public-certificates/ca_certificates/dataworks/dataworks_root_ca.pem",
    "s3://${local.env_certificate_bucket}/ca_certificates/dataworks/ca.pem",
    "s3://dw-management-dev-public-certificates/ca_certificates/dataworks/ca.pem",
    "s3://${data.terraform_remote_state.mgmt_ca.outputs.public_cert_bucket.id}/ca_certificates/dataworks/root_ca.pem"
  ]
}

variable "emr_ami_id" {
  description = "AMI ID to use for the HBase EMR nodes"
}

variable "emr_instance_type" {
  default = {
    development = "m5.2xlarge"
    qa          = "m5.2xlarge"
    integration = "m5.2xlarge"
    preprod     = "m5.2xlarge"
    production  = "m5.2xlarge"
  }
}
