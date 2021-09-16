#!/bin/bash

EQUALITY_DATABASE="uc_equality"

(
    # Import the logging functions
    source /opt/emr/logging.sh

    # Import and execute resume step function
    source /opt/emr/resume_step.sh

    function log_wrapper_message() {
        log_adg_message "$${1}" "equalities.sh" "Running as: ,$USER"
    }

    log_wrapper_message "creating equalities managed table if doesnt exist"
    hive --hivevar equality_database=$EQUALITY_DATABASE -f /var/ci/equality_managed_table.sql
    log_wrapper_message "Done creation of equalities managed table"
    
) >> /var/log/adg/equalities_managed.log 2>&1
