#!/usr/bin/env bash
# Publish only the tested tag artifacts; an existing public release is immutable.
set -euo pipefail
set +x
umask 077
: "${GITHUB_REPOSITORY:?}" "${RELEASE_TAG:?}" "${SOURCE_SHA:?}" "${COSIGN_PUBLIC_KEY_SHA256:?}"
: "${REGISTRY_PYTHON:?}" "${REGISTRY_SCRIPT:?}" "${REGISTRY_INFRASTRUCTURE:?}"
: "${COSIGN_PRIVATE_KEY:?}" "${COSIGN_PASSWORD:?}" "${TWINE_PASSWORD:?}"

directory="$(mktemp -d)"
##
# Remove only owned temporary release data and preserve the operation's exit status.
# -> ret::exit_code
cleanup() {
    status="$?"
    trap - EXIT
    rm -rf -- "$directory"
    exit "$status"
}
trap cleanup EXIT

git merge-base --is-ancestor "$SOURCE_SHA" origin/main
release_state="$(gh release list --repo "$GITHUB_REPOSITORY" --limit 100 --json tagName,isDraft --jq ".[] | select(.tagName == \"$RELEASE_TAG\") | .isDraft")"
if [ "$release_state" = false ]; then
    bash scripts/release/verify-published.sh
    exit 0
fi
cp dist/*.whl dist/*.tar.gz dist/artifact-provenance.json "$directory/"
python scripts/release/attest.py prepare --directory "$directory" --tag "$RELEASE_TAG" --source "$SOURCE_SHA" --fingerprint "$COSIGN_PUBLIC_KEY_SHA256"
if [ -z "$release_state" ]; then
    gh release create "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --verify-tag --draft --title "Argivore $RELEASE_TAG" --notes-file "$RUNNER_TEMP/release-notes.md"
else
    # Check existing payload bytes before retrying draft attachments. Signatures may be renewed.
    mkdir "$directory/previous"
    gh release download "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --dir "$directory/previous"
    for file in "$directory/previous/"*.whl "$directory/previous/"*.tar.gz; do
        [ -e "$file" ] || continue
        cmp "$file" "$directory/$(basename "$file")"
    done
    rm -rf -- "$directory/previous"
fi
# Small provenance files precede payloads so interrupted uploads retain useful metadata.
python scripts/release/upload.py "$directory"
mkdir "$directory/download"
gh release download "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --dir "$directory/download"
python scripts/release/attest.py verify --directory "$directory/download" --tag "$RELEASE_TAG" --source "$SOURCE_SHA" --fingerprint "$COSIGN_PUBLIC_KEY_SHA256"
"$REGISTRY_PYTHON" "$REGISTRY_SCRIPT" artifacts publish python \
    --directory dist --receipt dist/artifact-provenance.json --source-sha "$SOURCE_SHA" \
    --infrastructure "$REGISTRY_INFRASTRUCTURE"
gh release edit "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --draft=false
