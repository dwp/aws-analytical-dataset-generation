#!/bin/bash

# This script waits for a fixed period to give the metrics scraper enough
# time to collect ADGs metrics. It then deletes all of ADGs metrics so that
# the scraper doesn't continually gather stale metrics long past ADG's termination.

set -euo pipefail
(
    # Import the logging functions

    # shellcheck source=/opt/emr/logging.sh
    source /opt/emr/logging.sh
    
    # Import and execute resume step function
    source /opt/emr/resume_step.sh
    
    function log_wrapper_message() {
        log_adg_message "$${1}" "flush-pushgateway.sh" "Running as: ,$USER"
    }
    
    log_wrapper_message "Sleeping for 3m"
    
    sleep 180 # scrape interval is 60, scrape timeout is 10, 5 for the pot
    
    log_wrapper_message "Flushing the ADG pushgateway"
    curl -X PUT "http://${adg_pushgateway_hostname}:9091/api/v1/admin/wipe"
    log_wrapper_message "Done flushing the ADG pushgateway"
    
) >> /var/log/adg/flush-pushgateway.log 2>&1
