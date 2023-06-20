#!/usr/bin/env bash
(
    sudo echo -e "yarn - nofile {$yarn_nofile_limit}\nyarn - noproc ${yarn_noproc_limit}\n" > /etc/security/limits.d/yarn.conf

) >> /var/log/adg/ulimit.log 2>&1
