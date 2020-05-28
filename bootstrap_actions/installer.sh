(
# Import the logging functions
source /opt/emr/logging.sh

function log_wrapper_message() {
    log_adg_message "$${1}" "installer.sh" "$${PID}" "$${@:2}" "Running as: ,$USER"
}

log_wrapper_message "Setting up the HTTP, NO_PROXY & HTTPS Proxy"

FULL_PROXY="${full_proxy}"
FULL_NO_PROXY="${full_no_proxy}"
export http_proxy="$FULL_PROXY"
export HTTP_PROXY="$FULL_PROXY"
export https_proxy="$FULL_PROXY"
export HTTPS_PROXY="$FULL_PROXY"
export no_proxy="$FULL_NO_PROXY"
export NO_PROXY="$FULL_NO_PROXY"

log_wrapper_message "Installing boto3 packages"

sudo -E /usr/bin/pip-3.6 install boto3 >> /var/log/adg/install-boto3.log 2>&1

sudo -E /usr/bin/pip-3.6 install requests >> /var/log/adg/install-requests.log 2>&1

sudo -E /usr/bin/pip-3.6 install pycrypto >> /var/log/adg/install-pycrypto.log 2>&1

log_wrapper_message "Completed the installer.sh step of the EMR Cluster"

) >> /var/log/adg/nohup.log 2>&1
