FULL_PROXY="${full_proxy}"
FULL_NO_PROXY="${full_no_proxy}"
export http_proxy="$FULL_PROXY"
export HTTP_PROXY="$FULL_PROXY"
export https_proxy="$FULL_PROXY"
export HTTPS_PROXY="$FULL_PROXY"
export no_proxy="$FULL_NO_PROXY"
export NO_PROXY="$FULL_NO_PROXY"


sudo chown hadoop:hadoop /usr/lib/python3.6/dist-packages
sudo chown hadoop:hadoop /usr/lib64/python3.6/dist-packages
sudo chown hadoop:hadoop /usr/bin
sudo chown hadoop:hadoop /usr/bin/rst2html.py

/usr/bin/pip-3.6 install boto3
/usr/bin/pip-3.6 install happybase