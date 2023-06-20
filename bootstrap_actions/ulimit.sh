#!/usr/bin/env bash
(

    echo "Configuring yarn nofile limit"
    sidp echo -e "yarn - nofile ${yarn_nofiles_limit}\nyarn - noproc ${yarn_nofiles_limit}" > /etc/security/limits.d/yarn.conf
    echo "Configured yarn nofile limit successfully."
) >> /var/log/adg/ulimit.log 2>&1
