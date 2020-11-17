variable "emr_release_label" {
  description = "Version of AWS EMR to deploy with associated applicatoins"
  default     = "emr-5.29.0"
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

variable "emr_release" {
  default = {
    development = "5.29.0"
    qa          = "5.29.0"
    integration = "5.29.0"
    preprod     = "5.29.0"
    production  = "5.29.0"
  }
}

variable "emr_instance_type" {
  default = {
    development = "m5.8xlarge"
    qa          = "m5.8xlarge"
    integration = "m5.8xlarge"
    preprod     = "m5.8xlarge"
    production  = "m5.8xlarge"
  }
}

variable "emr_core_instance_count" {
  default = {
    development = "2"
    qa          = "2"
    integration = "2"
    preprod     = "1"
    production  = "20"
  }
}

variable "emr_num_cores_per_core_instance" {
  default = {
    development = "32"
    qa          = "32"
    integration = "32"
    preprod     = "48"
    production  = "48"
  }
}

variable "spark_kyro_buffer" {
  default = {
    development = "128"
    qa          = "128"
    integration = "128"
    preprod     = "2047m"
    production  = "2047m"
  }
}


# Note this isn't the amount of RAM the instance has; it's the maximum amount
# that EMR automatically configures for YARN. See
# https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-hadoop-task-config.html
# (search for yarn.nodemanager.resource.memory-mb)
variable "emr_yarn_memory_gb_per_core_instance" {
  default = {
    development = "120"
    qa          = "120"
    integration = "120"
    preprod     = "184"
    production  = "184"
  }
}

variable "metadata_store_master_username" {
  description = "Username for metadata store master RDS user"
  default     = "hive"
}

variable "metadata_store_adg_reader_username" {
  description = "Username for metadata store readonly RDS user"
  default     = "adg-reader"
}

variable "metadata_store_adg_writer_username" {
  description = "Username for metadata store writer RDS user"
  default     = "adg-writer"
}

variable "metadata_store_pdm_writer_username" {
  description = "Username for metadata store writer RDS user"
  default     = "pdm-writer"
}

variable "metadata_store_analytical_env_username" {
  description = "Username for metadata store writer Analytical Environment user"
  default     = "analytical-env"
}

variable "metadata_store_bgdc_username" {
  description = "Username for metadata store reader BGDC user"
  default     = "bgdc"
}

variable "htme_data_location" {
  default = {
    development = "businessdata/mongo/ucdata/2020-07-06/full/"
    qa          = "businessdata/mongo/ucdata/2020-07-06/full/"
    integration = "businessdata/mongo/ucdata/2020-08-07/full/"
    preprod     = "businessdata/mongo/ucdata/2020-07-06/full/"
    production  = "businessdata/mongo/ucdata/2020-07-26/full/"
  }
}
