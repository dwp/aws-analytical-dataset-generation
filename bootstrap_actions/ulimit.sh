#!/usr/bin/env bash
(

    echo "Configuring yarn nofile limit"
    sudo touch /etc/security/limits.d/yarn.conf
cat >> /etc/security/limits.d/yarn.conf <<EOF
yarn - nofile ${yarn_nofiles_limit}
yarn - noproc ${yarn_nofiles_limit}
EOF
    echo "Configured yarn nofile limit successfully."
) >> /var/log/adg/ulimit.log 2>&1
