#!/usr/bin/env bash


VERSION=$(curl --silent "https://api.github.com/repos/dwp/${REPO}/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')

NAME

update_tfvars() {
    echo "$(echo ${REPO} | sed 's/-/_/g')_zip = { base_path = \"../${REPO}-release\", version = \"${VERSION}\" }" >> terraform.tfvars
}

get_release() {
    type=$1
    ASSET=$(curl --silent "https://api.github.com/repos/dwp/${REPO}/releases/latest" | grep "browser_download_url.*zip" | cut -d : -f 2,3 | tr -d \")
    ASSET=$(curl --silent "https://api.github.com/repos/dwp/${REPO}/releases/latest" | grep "browser_download_url.*zip" | cut -d : -f 2,3 | tr -d \")

    RESPONSE=
    for k in $(jq '.assets | keys | .[]' <<< "$resp"); do
    value=$(jq -r ".assets[$k]" <<< $resp);
    url=$(jq -r ".browser_download_url" <<< $value);
    release=${REPO}-$VERSION
    echo $url
    if  echo "$url" | grep -q "$release"; then
        export ASSET=$url
        echo "correct $url"
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
        get_re

        (cd ../${REPO}-release/ && curl -L -O ${ASSET})
fi

}




