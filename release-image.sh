#!/bin/bash
VERSION=$(cat VERSION)
DRY_RUN=false
GITHUB_USERNAME=${GITHUB_USERNAME:-}
GITHUB_TOKEN=${GITHUB_TOKEN:-}

info() {
  echo -e "\033[0;32m$1\033[0m"
}

warn() {
  echo -e "\033[0;93m$1\033[0m"
}

error() {
  echo -e "\033[0;91m$1\033[0m" >&2
}

if ! command -v curl > /dev/null; then
  error "[Fail] Not install curl"
  exit 1
fi

if [ "${1:-}" == "--dry-run" ]; then
  warn "[Dry run mode]"
  DRY_RUN=true
fi

tag="$VERSION"
name="primehub-usage $VERSION"
info "[Release] Primehub-usage with version $VERSION"
echo "  name: $name"
echo "  tag:  $tag"

if [ "$GITHUB_USERNAME" == "" ]; then
  read -p "Please provide Github username: " GITHUB_USERNAME
fi
if [ "$GITHUB_TOKEN" == "" ]; then
  read -s -p "Please provide Github token: " GITHUB_TOKEN
  echo ""
fi

info "[Auth] Github"
echo "Username: $GITHUB_USERNAME"
echo "Token:    $(echo "$GITHUB_TOKEN" | sed "s/\(.\{6\}\).*/\1********/g")"

if [ "$DRY_RUN" == false ]; then
  info "[Create] release $name with tag $tag"
  curl \
    -i \
    -u ${GITHUB_USERNAME}:${GITHUB_TOKEN} \
    -X POST \
    -H "Accept: application/vnd.github.v3+json" \
    https://api.github.com/repos/infuseai/primehub-usage/releases \
    -d "{\"tag_name\":\"$tag\", \"name\":\"$name\"}"
 fi