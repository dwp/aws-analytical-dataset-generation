#!/usr/bin/env bash
(
    echo "Configuring yarn ulimit"
    sed -i "/nofile/c\yarn - nofile ${yarn_nofiles_limit}" /etc/security/limits.d/yarn.conf
    if [[ $? -eq 0 ]]; then
        echo "Configured yarn nofile limit successfully."
    else
        echo "Failed to udpate yarn nofile limit. It will default to 32578."
    fi

) >> /var/log/adg/ulimit.log 2>&1
