#!/bin/bash

set -Eeuo pipefail

cwa_metrics_collection_interval="$1"
cwa_namespace="$2"
cwa_log_group_name="$3"

export AWS_DEFAULT_REGION="${4}"

# Create config file required for CloudWatch Agent
mkdir -p /opt/aws/amazon-cloudwatch-agent/etc
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json <<CWAGENTCONFIG
{
  "agent": {
    "metrics_collection_interval": ${cwa_metrics_collection_interval},
    "logfile": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log"
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log",
            "log_group_name": "${cwa_log_group_name}",
            "log_stream_name": "amazon-cloudwatch-agent.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/messages",
            "log_group_name": "${cwa_log_group_name}",
            "log_stream_name": "messages",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/secure",
            "log_group_name": "${cwa_log_group_name}",
            "log_stream_name": "{instance_id}-secure",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/cloud-init-output.log",
            "log_group_name": "${cwa_log_group_name}",
            "log_stream_name": "{instance_id}-cloud-init-output.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/hive_tables_creation_log.log",
            "log_group_name": "${cwa_log_group_name}",
            "log_stream_name": "hive_tables_creation_log.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/install-pycrypto.log",
            "log_group_name": "${cwa_log_group_name}",
            "log_stream_name": "install-pycrypto.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/install-requests.log",
            "log_group_name": "${cwa_log_group_name}",
            "log_stream_name": "install-requests.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/install-boto3.log",
            "log_group_name": "${cwa_log_group_name}",
            "log_stream_name": "install-boto3.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/create_hive_tables.log",
            "log_group_name": "${cwa_log_group_name}",
            "log_stream_name": "create_hive_tables.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/generate_analytical_dataset.log",
            "log_group_name": "${cwa_log_group_name}",
            "log_stream_name": "generate_analytical_dataset.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/nohup.log",
            "log_group_name": "${cwa_log_group_name}",
            "log_stream_name": "nohup.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/acm-cert-retriever.log",
            "log_group_name": "${cwa_log_group_name}",
            "log_stream_name": "acm-cert-retriever.log",
            "timezone": "UTC"
          }
        ]
      }
    },
    "log_stream_name": "${cwa_namespace}",
    "force_flush_interval" : 15
  }
}
CWAGENTCONFIG

# Download and install CloudWatch Agent
curl https://s3.${AWS_DEFAULT_REGION}.amazonaws.com/amazoncloudwatch-agent-${AWS_DEFAULT_REGION}/centos/amd64/latest/amazon-cloudwatch-agent.rpm -O
rpm -U ./amazon-cloudwatch-agent.rpm
# To maintain CIS compliance
usermod -s /sbin/nologin cwagent

start amazon-cloudwatch-agent
