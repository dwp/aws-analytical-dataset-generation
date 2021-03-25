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
    production  = "m5.24xlarge"
  }
}

variable "emr_instance_type_core_one" {
  default = {
    development = "m5.4xlarge"
    qa          = "m5.4xlarge"
    integration = "m5.4xlarge"
    preprod     = "m5.4xlarge"
    production  = "m5.24xlarge"
  }
}

variable "emr_instance_type_core_two" {
  default = {
    development = "m5a.4xlarge"
    qa          = "m5a.4xlarge"
    integration = "m5a.4xlarge"
    preprod     = "m5a.4xlarge"
    production  = "m5a.24xlarge"
  }
}

variable "emr_instance_type_core_three" {
  default = {
    development = "r5a.4xlarge"
    qa          = "r5a.4xlarge"
    integration = "r5a.4xlarge"
    preprod     = "r5a.4xlarge"
    production  = "r5a.24xlarge"
  }
}

variable "emr_instance_type_core_four" {
  default = {
    development = "r5.4xlarge"
    qa          = "r5.4xlarge"
    integration = "r5.4xlarge"
    preprod     = "r5.4xlarge"
    production  = "r5.24xlarge"
  }
}

variable "emr_core_instance_count" {
  default = {
    development = "10"
    qa          = "10"
    integration = "10"
    preprod     = "10"
    production  = "25"
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
    production  = 350 # More than possible as it won't create them if no core or memory available
  }
}


# Note this isn't the amount of RAM the instance has; it's the maximum amount
# that EMR automatically configures for YARN. See
# https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-hadoop-task-config.html
# (search for yarn.nodemanager.resource.memory-mb)
variable "emr_yarn_memory_gb_per_core_instance" {
  default = {
    development = "48"  # Set for m5.4xlarge
    qa          = "48"  # Set for m5.4xlarge
    integration = "48"  # Set for m5.4xlarge
    preprod     = "48"  # Set for m5.4xlarge
    production  = "376" # Set for m5.24xlarge
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

# See https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-hadoop-task-config.html#emr-hadoop-task-config-m5 for yarn configuration justifications

variable "yarn_map_memory_mb" {
  default = {
    development = "3072"
    qa          = "3072"
    integration = "3072"
    preprod     = "3072"
    production  = "4011"
  }
}

variable "yarn_reduce_memory_mb" {
  default = {
    development = "6144"
    qa          = "6144"
    integration = "6144"
    preprod     = "6144"
    production  = "8022"
  }
}

variable "yarn_app_mapreduce_am_resource_mb" {
  default = {
    development = "6144"
    qa          = "6144"
    integration = "6144"
    preprod     = "6144"
    production  = "8022"
  }
}

variable "yarn_map_java_opts" {
  default = {
    development = "-Xmx2458m"
    qa          = "-Xmx2458m"
    integration = "-Xmx2458m"
    preprod     = "-Xmx2458m"
    production  = "-Xmx3209m"
  }
}

variable "yarn_reduce_java_opts" {
  default = {
    development = "-Xmx4916m"
    qa          = "-Xmx4916m"
    integration = "-Xmx4916m"
    preprod     = "-Xmx4916m"
    production  = "-Xmx6418m"
  }
}

variable "yarn_min_allocation_mb" {
  default = {
    development = "512"
    qa          = "512"
    integration = "512"
    preprod     = "512"
    production  = "1024"
  }
}

variable "yarn_max_allocation_mb" {
  default = {
    development = "24576"
    qa          = "24576"
    integration = "24576"
    preprod     = "24576"
    production  = "385024"
  }
}

variable "yarn_node_manager_resource_mb" {
  default = {
    development = "24576"
    qa          = "24576"
    integration = "24576"
    preprod     = "24576"
    production  = "385024"
  }
}
