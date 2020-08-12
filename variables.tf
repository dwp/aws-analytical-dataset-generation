variable "emr_release_label" {
  description = "Version of AWS EMR to deploy with associated applicatoins"
  default     = "emr-5.24.1"
}

variable "emr_applications" {
  description = "List of applications to deploy to EMR Cluster"
  type        = list(string)
  default     = ["Spark", "HBase", "Hive", "Ganglia"]
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
  default     = ["dataworks_root_ca", "dataworks_mgt_root_ca"]
}

variable "emr_ami_id" {
  description = "AMI ID to use for the HBase EMR nodes"
}

variable "analytical_dataset_generation_exporter_jar" {
  type = map(string)

  default = {
    base_path = ""
    version   = ""
  }
}

variable "emr_instance_type" {
  default = {
    development = "m5.8xlarge"
    qa          = "m5.2xlarge"
    integration = "m5.8xlarge"
    preprod     = "m5.2xlarge"
    production  = "m5.24xlarge"
  }
}

variable "emr_core_instance_count" {
  default = {
    development = "2"
    qa          = "2"
    integration = "2"
    preprod     = "25"
    production  = "25"
  }
}

variable "emr_num_cores_per_core_instance" {
  default = {
    development = "16"
    qa          = "16"
    integration = "16"
    preprod     = "48"
    production  = "48"
  }
}

variable "emr_memory_gb_per_core_instance" {
  default = {
    development = "64"
    qa          = "64"
    integration = "64"
    preprod     = "192"
    production  = "192"
  }
}
