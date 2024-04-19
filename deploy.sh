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

    docker buildx build \
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
        --exclude ".venv" \
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

    docker build -t bbilly1/redditbot .
    docker compose up -d

}

function validate {

    if [[ $1 ]]; then
        check_path="$1"
    else
        check_path="."
    fi

    echo "run validate on $check_path"

    # note: this logic is duplicated in the `./github/workflows/lint_python.yml` config
    # if you update this file, you should update that as well
    echo "running black"
    black --force-exclude "migrations/*" --diff --color --check -l 120 "$check_path"
    echo "running codespell"
    codespell --skip="./.git,./.venv,./.mypy_cache" "$check_path"
    echo "running flake8"
    flake8 "$check_path" --exclude "migrations,.venv" --count --max-complexity=10 \
        --max-line-length=120 --show-source --statistics
    echo "running isort"
    isort --skip "migrations" --skip ".venv" --check-only --diff --profile black -l 120 "$check_path"
    printf "    \n> all validations passed\n"

}


if [[ $1 == "docker" ]]; then
    sync_docker
elif [[ $1 == "unstable" ]]; then
    sync_unstable
elif [[ $1 == "test" ]]; then
    sync_testing
elif [[ $1 == "validate" ]]; then
    validate "$2"
else
    echo "valid options are: test | docker | unstable | validate"
fi

##
exit 0
