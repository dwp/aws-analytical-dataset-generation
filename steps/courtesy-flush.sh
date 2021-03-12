#!/bin/bash

CORRELATION_ID=$2
S3_PREFIX=$4
SNAPSHOT_TYPE=$6
EXPORT_DATE=$8

set -euo pipefail
(
    # Set the ddb values as this is the initial step
    echo $CORRELATION_ID >>     /opt/emr/correlation_id.txt
    echo $S3_PREFIX >>          /opt/emr/s3_prefix.txt
    echo $SNAPSHOT_TYPE >>      /opt/emr/snapshot_type.txt
    echo $EXPORT_DATE >>        /opt/emr/export_date.txt

    # Import the logging functions
    source /opt/emr/logging.sh
    
    # Import and execute resume step function
    source /opt/emr/resume_step.sh
    
    function log_wrapper_message() {
        log_adg_message "$${1}" "flush-pushgateway.sh" "Running as: ,$USER"
    }
    
    log_wrapper_message "Flushing the ADG pushgateway"
    curl -X PUT http://${adg_pushgateway_hostname}:9091/api/v1/admin/wipe
    log_wrapper_message "Done flushing the ADG pushgateway"
    
) >> /var/log/adg/flush-pushgateway.log 2>&1
