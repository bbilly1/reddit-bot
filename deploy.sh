#!/bin/bash
# deploy to docker and local

function sync_docker() {

    if [[ $(systemctl is-active docker) != 'active' ]]; then
        echo "starting docker"
        sudo systemctl start docker
    fi

    echo "latest tags:"
    git tag | tail -n 5 | sort -r

    printf "\ncreate new version:\n"
    read -r VERSION

    sudo docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
    sudo docker buildx build \
        --platform linux/amd64,linux/arm64 \
        -t bbilly1/redditbot \
        -t bbilly1/redditbot:"$VERSION" --push .

    # create release tag
    echo "commits since last version:"
    git log "$(git describe --tags --abbrev=0)"..HEAD --oneline
    git tag -a "$VERSION" -m "new release version $VERSION"
    git push origin "$VERSION"

}

if [[ $1 == "docker" ]]; then
    sync_docker
else
    echo "valid options are: docker"
fi

##
exit 0
