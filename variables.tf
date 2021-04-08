variable "emr_release_label" {
  description = "Version of AWS EMR to deploy with associated applicatoins"
  default     = "emr-6.2.0"
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
  default     = "ami-0672faa58b65ff88d"
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
    development = "6.2.0"
    qa          = "6.2.0"
    integration = "6.2.0"
    preprod     = "6.2.0"
    production  = "6.2.0"
  }
}

variable "emr_instance_type_master" {
  default = {
    development = "m5.4xlarge"
    qa          = "m5.4xlarge"
    integration = "m5.4xlarge"
    preprod     = "m5.4xlarge"
    production  = "m5.16xlarge"
  }
}

variable "emr_instance_type_core_one" {
  default = {
    development = "m5.4xlarge"
    qa          = "m5.4xlarge"
    integration = "m5.4xlarge"
    preprod     = "m5.4xlarge"
    production  = "m5.16xlarge"
  }
}

# Count of instances
variable "emr_core_instance_count" {
  default = {
    development = "10"
    qa          = "10"
    integration = "10"
    preprod     = "10"
    production  = "39"
  }
}

variable "spark_kyro_buffer" {
  default = {
    development = "128m"
    qa          = "128m"
    integration = "128m"
    preprod     = "128m"
    production  = "2047m" # Max amount allowed
  }
}

variable "spark_executor_instances" {
  default = {
    development = 50
    qa          = 50
    integration = 50
    preprod     = 50
    production  = 600 # More than possible as it won't create them if no core or memory available
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
  default     = "bgdc-reader"
}

variable "metadata_store_kickstart_username" {
  description = "Username for metadata store writer Kickstart ADG user"
  default     = "kickstart-adg-writer"
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
