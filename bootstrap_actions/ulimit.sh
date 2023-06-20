#!/usr/bin/env bash
(
    sudo echo -e "yarn - nofile {$yarn_nofiles_limit}\nyarn - noproc ${yarn_nofiles_limit}\n" > /etc/security/limits.d/yarn.conf

) >> /var/log/adg/ulimit.log 2>&1
