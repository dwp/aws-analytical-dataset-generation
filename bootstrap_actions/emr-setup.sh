#!/usr/bin/env bash
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
    log_adg_message "$${1}" "emr-setup.sh" "$${PID}" "$${@:2}" "Running as: ,$USER"
}

log_wrapper_message "Setting up the Proxy"

echo -n "Running as: "
whoami

export AWS_DEFAULT_REGION=${aws_default_region}
export HTTP_PROXY="${http_proxy}"
export HTTPS_PROXY="${http_proxy}"
export NO_PROXY="${no_proxy}"

log_wrapper_message "Getting the DKS Certificate Details "

export ACM_KEY_PASSWORD=$(uuidgen -r)
log_wrapper_message "Retrieving the ACM Certificate details"

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
