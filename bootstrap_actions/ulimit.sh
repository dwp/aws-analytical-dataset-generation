#!/usr/bin/env bash
echo "Configuring ulimits"
(
    # Import the logging functions
    source /opt/emr/logging.sh

    function log_wrapper_message() {
        log_adg_message "$${1}" "ulimit.sh" "$${PID}" "$${@:2}" "Running as: ,$USER"
    }

    sudo sed -i "/nofile/c\yarn - nofile ${yarn_nofiles_limit}" /etc/security/limits.d/yarn.conf
) >> /var/log/adg/ulimit-yarn.log 2>&1
