#!/bin/bash
echo "Installing logging helper scripts"
sudo install -o hadoop -g hadoop -m 0700 -d /opt/emr /opt/shared /var/log/adg
echo "${adg_version}" > /opt/emr/version
echo "${adg_log_level}" > /opt/emr/log_level
echo "${environment_name}" > /opt/emr/environment
aws s3 cp "${s3_common_logging_shell}"   /opt/shared/common_logging.sh
aws s3 cp "${s3_logging_shell}"          /opt/emr/logging.sh
chmod u+x /opt/shared/common_logging.sh
chmod u+x /opt/emr/logging.sh

(
source /opt/emr/logging.sh

function log_wrapper_message() {
    log_adg_message "$${1}" "emr-setup.sh" "$${PID}" "$${@:2}" "Running as: $USER"
}

log_wrapper_message "Retrieving TLS certficate"

export AWS_DEFAULT_REGION=${aws_default_region}
export HTTP_PROXY="${http_proxy}"
export HTTPS_PROXY="${http_proxy}"
export NO_PROXY="${no_proxy}"
export ACM_KEY_PASSWORD=$(uuidgen -r)

sudo -E /usr/local/bin/acm-cert-retriever \
    --acm-cert-arn "${acm_cert_arn}" \
    --acm-key-passphrase "$ACM_KEY_PASSWORD" \
    --private-key-alias "${private_key_alias}" \
    --truststore-aliases "${truststore_aliases}" \
    --truststore-certs "${truststore_certs}"  >> /var/log/adg/acm-cert-retriever.log 2>&1

sudo chown hadoop:hadoop /etc/pki/tls/private/"${private_key_alias}".key

# TODO: Find a better way of doing this; it doesn't pin to specific dependency versions
# https://developerzen.com/best-practices-writing-production-grade-pyspark-jobs-cb688ac4d20f
# has an approach that may work
log_wrapper_message "Installing Python dependencies"
sudo -E /usr/bin/pip-3.6 install boto3 requests pycrypto >> /var/log/adg/install-python-deps.log 2>&1

log_wrapper_message "Completed cluster bootstrap actions"

) >> /var/log/adg/nohup.log 2>&1
