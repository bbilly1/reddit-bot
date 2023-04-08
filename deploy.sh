#!/bin/bash
# deploy to docker and local

remote_host="vps3"

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


function sync_unstable() {
    # copy project files to build image
    rsync -a --progress --delete-after \
        --exclude ".git" \
        --exclude ".gitignore" \
        --exclude ".vscode" \
        --exclude ".mypy_cache" \
        --exclude "env/" \
        --exclude "volume/" \
        --exclude "**/__pycache__/" \
        . -e ssh "$remote_host":redditbot
    
    ssh "$remote_host" 'docker build -t bbilly1/redditbot redditbot'
    ssh "$remote_host" 'docker compose -f docker/docker-compose.yml up -d'
}


function sync_testing() {

    if [[ $(systemctl is-active docker) != 'active' ]]; then
        echo "starting docker"
        sudo systemctl start docker
    fi

    sudo docker build -t bbilly1/redditbot .
    sudo docker compose up -d

}


if [[ $1 == "docker" ]]; then
    sync_docker
elif [[ $1 == "unstable" ]]; then
    sync_unstable
elif [[ $1 == "test" ]]; then
    sync_testing
else
    echo "valid options are: test | docker | unstable"
fi

##
exit 0
