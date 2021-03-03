#!/usr/bin/env bash
VERSION=$(curl --silent "https://api.github.com/repos/dwp/${REPO}/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
echo "my version is $VERSION"
echo >> terraform.tfvars
echo "$(echo ${REPO} | sed 's/-/_/g')_zip = { base_path = \"../${REPO}-release\", version = \"${VERSION}\" }" >> terraform.tfvars
mkdir ../${REPO}-release
ASSET=$(curl --silent "https://api.github.com/repos/dwp/${REPO}/releases/latest" | grep "browser_download_url.*zip" | cut -d : -f 2,3 | tr -d \")
ASSET2=$(curl --silent "https://api.github.com/repos/dwp/${REPO}/releases/latest" | grep "browser_download_url.*jar" | cut -d : -f 2,3 | tr -d \")

echo "my URL is https://api.github.com/repos/dwp/${REPO}/releases/latest"
(cd ../${REPO}-release/ && curl -L -O ${ASSET} || curl -L -O ${ASSET2} )
