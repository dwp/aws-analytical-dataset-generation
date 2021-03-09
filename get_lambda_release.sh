#!/usr/bin/env bash

get_release_information(){
    VERSION=$(curl --silent "https://api.github.com/repos/dwp/${REPO}/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
    RESPONSE=`echo $(curl --silent "https://api.github.com/repos/dwp/${REPO}/releases/latest")`
}

update_tfvars() {
    echo "$(echo ${REPO} | sed 's/-/_/g')_zip = { base_path = \"../${REPO}-release\", version = \"${VERSION}\" }" >> terraform.tfvars
}

get_release() {
    get_release_information
    for k in $(jq '.assets | keys | .[]' <<< "$RESPONSE"); do
        value=$(jq -r ".assets[$k]" <<< $RESPONSE);
        url=$(jq -r ".browser_download_url" <<< $value);
        if  echo "$url" | grep -q "$VERSION"; then
            export ASSET=$url
            fetch_asset
        fi
    done
}

fetch_asset(){
    EXISTING_VERSION=`ls ../${REPO}-release/ | grep ${VERSION}`

    if [[ -f ../${REPO}-release/$EXISTING_VERSION ]]; then
        echo "${REPO}-release/$EXISTING_VERSION already exists: Skipping download"
        update_tfvars
    else
        update_tfvars
        mkdir ../${REPO}-release
        (cd ../${REPO}-release/ && curl -L -O ${ASSET})
    fi
}

get_release

