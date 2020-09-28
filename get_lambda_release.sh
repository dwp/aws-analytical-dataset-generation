#!/usr/bin/env bash
VERSION=$(curl --silent "https://api.github.com/repos/dwp/${REPO}/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
echo "my version is $VERSION"
echo "$(echo ${REPO} | sed 's/-/_/g')_zip = { base_path = \"../${REPO}-release\", version = \"${VERSION}\" }" >> terraform.tfvars
mkdir ../${REPO}-release
ASSET=$(curl --silent "https://api.github.com/repos/dwp/${REPO}/releases/latest" | grep "browser_download_url.*zip" | cut -d : -f 2,3 | tr -d \")
(cd ../${REPO}-release/ && curl -O ${ASSET})
