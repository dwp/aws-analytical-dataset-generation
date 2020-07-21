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
  default     = ["dataworks_root_ca", "dataworks_mgt_root_ca", "ca_cert", "mgmt_cert", "root_ca"]
}

variable "emr_ami_id" {
  description = "AMI ID to use for the HBase EMR nodes"
}

variable "emr_instance_type" {
  default = {
    development = "m5.8xlarge"
    qa          = "m5.2xlarge"
    integration = "m5.8xlarge"
    # temp increase for DW-4437 testing
    preprod    = "m5.2xlarge"
    production = "m5.24xlarge"
  }
}

  variable "emr_no_core_nodes" {
  default = {
    development = "2"
    qa          = "2"
    integration = "2"
    preprod     = "2"
    production  = "12"
  }
}

variable "emr_maxExecutors" {
  default = {
    development = "20"
    qa          = "20"
    integration = "20"
    preprod     = "20"
    production  = "1100"
  }
}

variable "emr_minExecutors" {
  default = {
    development = "10"
    qa          = "10"
    integration = "10"
    preprod     = "10"
    production  = "100"
  }
}

variable "emr_core_instance_type_1" {
  default = {
    development = "m5.8xlarge"
    qa          = "m5.2xlarge"
    integration = "m5.8xlarge"
    preprod     = "m5.2xlarge"
    production  = "m5.24xlarge"
  }
}


variable "emr_core_instance_type_2" {
  default = {
    development = "m5.8xlarge"
    qa          = "m5.2xlarge"
    integration = "m5.8xlarge"
    preprod     = "m5.2xlarge"
    production  = "m5.12xlarge"
  }
}


variable "emr_weightedcapacity_1" {
  default = {
    development = "2"
    qa          = "2"
    integration = "2"
    preprod     = "2"
    production  = "12"
  }
}

variable "emr_weightedcapacity_2" {
  default = {
    development = "2"
    qa          = "2"
    integration = "2"
    preprod     = "2"
    production  = "24"
  }
}







