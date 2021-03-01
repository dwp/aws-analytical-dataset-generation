#!/bin/bash

# Set the ddb values as this is the initial step
CORRELATION_ID=$2
S3_PREFIX=$4
echo $CORRELATION_ID >>     /opt/emr/correlation_id.txt
echo $S3_PREFIX >>          /opt/emr/s3_prefix.txt

set -euo pipefail
(
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
