#!/usr/bin/env bash
echo "Creating shared directory"
sudo mkdir -p /opt/shared
sudo mkdir -p /opt/emr
sudo mkdir -p /var/log/adg
sudo chown hadoop:hadoop /opt/emr
sudo chown hadoop:hadoop /opt/shared
sudo chown hadoop:hadoop /var/log/adg
echo "${VERSION}" > /opt/emr/version
echo "${ADG_LOG_LEVEL}" > /opt/emr/log_level
echo "${ENVIRONMENT_NAME}" > /opt/emr/environment

echo "Installing scripts"
aws s3 cp "${S3_COMMON_LOGGING_SHELL}"        /opt/shared/common_logging.sh
aws s3 cp "${S3_LOGGING_SHELL}"               /opt/emr/logging.sh
aws s3 cp "${S3_CLOUDWATCH_SHELL}"            /opt/emr/cloudwatch.sh
aws s3 cp "${S3_SEND_SNS_NOTIFICATION}"       /opt/emr/send_notification.py

echo "Changing the Permissions"
chmod u+x /opt/shared/common_logging.sh
chmod u+x /opt/emr/logging.sh
chmod u+x /opt/emr/cloudwatch.sh
chmod u+x /opt/emr/send_notification.py

(
# Import the logging functions
source /opt/emr/logging.sh

function log_wrapper_message() {
    log_adg_message "$${1}" "emr-setup.sh" "$${PID}" "$${@:2}" "Running as: ,$USER"
}

log_wrapper_message "Setting up the Proxy"

echo -n "Running as: "
whoami

export AWS_DEFAULT_REGION=${aws_default_region}

FULL_PROXY="${full_proxy}"
FULL_NO_PROXY="${full_no_proxy}"
export http_proxy="$FULL_PROXY"
export HTTP_PROXY="$FULL_PROXY"
export https_proxy="$FULL_PROXY"
export HTTPS_PROXY="$FULL_PROXY"
export no_proxy="$FULL_NO_PROXY"
export NO_PROXY="$FULL_NO_PROXY"
export ADG_LOG_LEVEL="${ADG_LOG_LEVEL}"

echo "Setup cloudwatch logs"
sudo /opt/emr/cloudwatch.sh \
    "${cwa_metrics_collection_interval}" "${cwa_namespace}"  "${cwa_log_group_name}" \
    "${aws_default_region}" "${cwa_bootstrap_loggrp_name}" "${cwa_steps_loggrp_name}" \
    "${cwa_yarnspark_loggrp_name}"

export ACM_KEY_PASSWORD=$(uuidgen -r)

log_wrapper_message "Getting the DKS Certificate Details "

## get dks cert
export TRUSTSTORE_PASSWORD=$(uuidgen -r)
export KEYSTORE_PASSWORD=$(uuidgen -r)
export PRIVATE_KEY_PASSWORD=$(uuidgen -r)
export ACM_KEY_PASSWORD=$(uuidgen -r)

#sudo mkdir -p /opt/emr
#sudo chown hadoop:hadoop /opt/emr
touch /opt/emr/dks.properties
cat >> /opt/emr/dks.properties <<EOF
identity.store.alias=${private_key_alias}
identity.key.password=$PRIVATE_KEY_PASSWORD
spark.ssl.fs.enabled=true
spark.ssl.keyPassword=$KEYSTORE_PASSWORD
identity.keystore=/opt/emr/keystore.jks
identity.store.password=$KEYSTORE_PASSWORD
trust.keystore=/opt/emr/truststore.jks
trust.store.password=$TRUSTSTORE_PASSWORD
data.key.service.url=${dks_endpoint}
EOF

log_wrapper_message "Retrieving the ACM Certificate details"

/usr/local/bin/acm-cert-retriever \
    --acm-cert-arn "${acm_cert_arn}" \
    --acm-key-passphrase "$ACM_KEY_PASSWORD" \
    --keystore-path "/opt/emr/keystore.jks" \
    --keystore-password "$KEYSTORE_PASSWORD" \
    --private-key-alias "${private_key_alias}" \
    --private-key-password "$PRIVATE_KEY_PASSWORD" \
    --truststore-path "/opt/emr/truststore.jks" \
    --truststore-password "$TRUSTSTORE_PASSWORD" \
    --truststore-aliases "${truststore_aliases}" \
    --truststore-certs "${truststore_certs}" \
    --jks-only true >> /var/log/adg/acm-cert-retriever.log 2>&1


sudo -E /usr/local/bin/acm-cert-retriever \
    --acm-cert-arn "${acm_cert_arn}" \
    --acm-key-passphrase "$ACM_KEY_PASSWORD" \
    --private-key-alias "${private_key_alias}" \
    --truststore-aliases "${truststore_aliases}" \
    --truststore-certs "${truststore_certs}"  >> /var/log/adg/acm-cert-retriever.log 2>&1

cd /etc/pki/ca-trust/source/anchors/
sudo touch analytical_ca.pem
sudo chown hadoop:hadoop /etc/pki/tls/private/"${private_key_alias}".key /etc/pki/tls/certs/"${private_key_alias}".crt /etc/pki/ca-trust/source/anchors/analytical_ca.pem
TRUSTSTORE_ALIASES="${truststore_aliases}"
for F in $(echo $TRUSTSTORE_ALIASES | sed "s/,/ /g"); do
 (sudo cat "$F.crt"; echo) >> analytical_ca.pem;
done

log_wrapper_message "Completed the emr-setup.sh step of the EMR Cluster"

) >> /var/log/adg/nohup.log 2>&1
