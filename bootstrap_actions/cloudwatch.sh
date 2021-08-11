#!/bin/bash

set -Eeuo pipefail

cwa_metrics_collection_interval="$1"
cwa_namespace="$2"
cwa_log_group_name="$3"
cwa_bootstrap_loggrp_name="$5"
cwa_steps_loggrp_name="$6"
cwa_yarnspark_loggrp_name="$7"
cwa_tests_loggrp_name="$8"
cwa_chrony_loggrp_name="$9"


export AWS_DEFAULT_REGION="$${4}"

# Create config file required for CloudWatch Agent
mkdir -p /opt/aws/amazon-cloudwatch-agent/etc
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json <<CWAGENTCONFIG
{
  "agent": {
    "metrics_collection_interval": $${cwa_metrics_collection_interval},
    "logfile": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log"
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log",
            "log_group_name": "$${cwa_log_group_name}",
            "log_stream_name": "{instance_id}-amazon-cloudwatch-agent.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/messages",
            "log_group_name": "$${cwa_log_group_name}",
            "log_stream_name": "{instance_id}-messages",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/secure",
            "log_group_name": "$${cwa_log_group_name}",
            "log_stream_name": "{instance_id}-secure",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/cloud-init-output.log",
            "log_group_name": "$${cwa_log_group_name}",
            "log_stream_name": "{instance_id}-cloud-init-output.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/acm-cert-retriever.log",
            "log_group_name": "$${cwa_bootstrap_loggrp_name}",
            "log_stream_name": "{instance_id}-acm-cert-retriever.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/hive_setup.log",
            "log_group_name": "$${cwa_bootstrap_loggrp_name}",
            "log_stream_name": "{instance_id}-hive_setup.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/installer.log",
            "log_group_name": "$${cwa_bootstrap_loggrp_name}",
            "log_stream_name": "{instance_id}-installer.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/metrics-setup.log",
            "log_group_name": "$${cwa_bootstrap_loggrp_name}",
            "log_stream_name": "{instance_id}-metrics-setup.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/emr-setup.log",
            "log_group_name": "$${cwa_bootstrap_loggrp_name}",
            "log_stream_name": "{instance_id}-emr-setup.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/install-pycrypto.log",
            "log_group_name": "$${cwa_bootstrap_loggrp_name}",
            "log_stream_name": "{instance_id}-install-pycrypto.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/update_dynamo_sh.log",
            "log_group_name": "$${cwa_bootstrap_loggrp_name}",
            "log_stream_name": "{instance_id}-update_dynamo_sh.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/download_scripts.log",
            "log_group_name": "$${cwa_bootstrap_loggrp_name}",
            "log_stream_name": "{instance_id}-download-scripts.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/install-requests.log",
            "log_group_name": "$${cwa_bootstrap_loggrp_name}",
            "log_stream_name": "{instance_id}-install-requests.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/install-boto3.log",
            "log_group_name": "$${cwa_bootstrap_loggrp_name}",
            "log_stream_name": "{instance_id}-install-boto3.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/status_metrics_sh.log",
            "log_group_name": "$${cwa_bootstrap_loggrp_name}",
            "log_stream_name": "{instance_id}-status_metrics_sh.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/hive-tables-creation.log",
            "log_group_name": "$${cwa_steps_loggrp_name}",
            "log_stream_name": "{instance_id}-hive-tables-creation.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/create-hive-tables.log",
            "log_group_name": "$${cwa_steps_loggrp_name}",
            "log_stream_name": "{instance_id}-create-hive-tables.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/generate-analytical-dataset.log",
            "log_group_name": "$${cwa_steps_loggrp_name}",
            "log_stream_name": "{instance_id}-generate-analytical-dataset.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/generate-analytical-dataset-historical-audit.log",
            "log_group_name": "$${cwa_steps_loggrp_name}",
            "log_stream_name": "{instance_id}-generate-analytical-dataset-historical-audit.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/generate-analytical-dataset-historical-equality.log",
            "log_group_name": "$${cwa_steps_loggrp_name}",
            "log_stream_name": "{instance_id}-generate-analytical-dataset-historical-equality.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/hadoop-yarn/containers/application_*/container_*/stdout**",
            "log_group_name": "$${cwa_yarnspark_loggrp_name}",
            "log_stream_name": "{instance_id}-spark-stdout.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/hadoop-yarn/containers/application_*/container_*/stderr**",
            "log_group_name": "$${cwa_yarnspark_loggrp_name}",
            "log_stream_name": "{instance_id}-spark-stderror.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/hadoop-yarn/yarn-yarn-nodemanager**.log",
            "log_group_name": "$${cwa_yarnspark_loggrp_name}",
            "log_stream_name": "{instance_id}-yarn_nodemanager.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/chrony/statistics.log",
            "log_group_name": "$${cwa_chrony_loggrp_name}",
            "log_stream_name": "{instance_id}-chrony-statistics.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/chrony/measurements.log",
            "log_group_name": "$${cwa_chrony_loggrp_name}",
            "log_stream_name": "{instance_id}-chrony-measurements.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/chrony/tracking.log",
            "log_group_name": "$${cwa_chrony_loggrp_name}",
            "log_stream_name": "{instance_id}-chrony-tracking.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/sns_notification.log",
            "log_group_name": "$${cwa_steps_loggrp_name}",
            "log_stream_name": "{instance_id}-sns_notification.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/flush-pushgateway.log",
            "log_group_name": "$${cwa_steps_loggrp_name}",
            "log_stream_name": "{instance_id}-flush-pushgateway.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/executeUpdateAppointment.log",
            "log_group_name": "$${cwa_steps_loggrp_name}",
            "log_stream_name": "{instance_id}-executeUpdateAppointment.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/adg/e2e.log",
            "log_group_name": "$${cwa_tests_loggrp_name}",
            "log_stream_name": "{instance_id}-e2e.log",
            "timezone": "UTC"
          }
        ]
      }
    },
    "log_stream_name": "$${cwa_namespace}",
    "force_flush_interval" : 15
  }
}
CWAGENTCONFIG

%{ if emr_release == "5.29.0" ~}
# Download and install CloudWatch Agent
curl https://s3.$${AWS_DEFAULT_REGION}.amazonaws.com/amazoncloudwatch-agent-$${AWS_DEFAULT_REGION}/centos/amd64/latest/amazon-cloudwatch-agent.rpm -O
rpm -U ./amazon-cloudwatch-agent.rpm
# To maintain CIS compliance
usermod -s /sbin/nologin cwagent

start amazon-cloudwatch-agent
%{ else ~}
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
systemctl start amazon-cloudwatch-agent
%{ endif ~}
