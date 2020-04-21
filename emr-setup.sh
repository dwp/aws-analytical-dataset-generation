#!/usr/bin/env bash

# Only execute below here on an EMR Master node
if [[ $(grep "isMaster" /mnt/var/lib/info/instance.json | grep true) ]]; then
    echo "I am a Master"
else
    echo "I am a Slave, exiting"
    exit 0
fi

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

export ACM_KEY_PASSWORD=$(uuidgen -r)

aws s3 cp "${hive-scripts-path}"  .
aws s3 cp "${collections_list}"  .

/usr/bin/python create-hive-tables.py

sudo mkdir -p /opt/emr
sudo chown hadoop:hadoop /opt/emr
touch /opt/emr/dks.properties
cat >> /opt/emr/dks.properties <<EOF
spark.ssl.fs.enabled=true
data.key.service.url=${dks_endpoint}
EOF

sudo -E /usr/local/bin/acm-cert-retriever \
    --acm-cert-arn "${acm_cert_arn}" \
    --acm-key-passphrase "$ACM_KEY_PASSWORD" \
    --private-key-alias "${private_key_alias}" \
    --truststore-aliases "${truststore_aliases}" \
    --truststore-certs "${truststore_certs}"

cd /etc/pki/ca-trust/source/anchors/
sudo touch analytical_ca.pem
sudo chown hadoop:hadoop /etc/pki/tls/private/"${private_key_alias}".key /etc/pki/tls/certs/"${private_key_alias}".crt /etc/pki/ca-trust/source/anchors/analytical_ca.pem
TRUSTSTORE_ALIASES="${truststore_aliases}"
for F in $(echo $TRUSTSTORE_ALIASES | sed "s/,/ /g"); do
 (sudo cat "$F.crt"; echo) >> analytical_ca.pem;
done

