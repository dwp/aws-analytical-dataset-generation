echo "Creating shared directory"
sudo mkdir -p /opt/shared
sudo mkdir -p /opt/emr
sudo chown hadoop:hadoop /opt/emr
sudo chown hadoop:hadoop /opt/shared
echo "$VERSION" > /opt/emr/version
echo "${ADG_LOG_LEVEL}" > /opt/emr/log_level
echo "${ENVIRONMENT_NAME}" > /opt/emr/environment

echo "Installing scripts"
s3 cp "$S3_COMMON_LOGGING_SHELL"   /opt/shared/common_logging.sh
s3 cp "$S3_LOGGING_SHELL"          /opt/emr/logging.sh

echo "Changing the Permissions"
chmod u+x /opt/shared/common_logging.sh
chmod u+x /opt/emr/logging.sh

# Import the logging functions
source /opt/emr/logging.sh

function log_wrapper_message() {
    log_adg_message "${1}" "installer.sh" "${PID}" "${@:2}" "Running as: ,$USER"
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

sudo -E /usr/bin/pip-3.6 install boto3
