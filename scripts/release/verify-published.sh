#!/usr/bin/env bash
# A successful pipeline must end in verified, public release and registry artifacts.
set -euo pipefail
: "${GITHUB_REPOSITORY:?}" "${RELEASE_TAG:?}" "${SOURCE_SHA:?}" "${COSIGN_PUBLIC_KEY_SHA256:?}"
directory="$(mktemp -d)"
##
# Remove downloaded public files while retaining the verifier's exit status.
# -> ret::exit_code
cleanup() {
    status="$?"
    trap - EXIT
    rm -rf -- "$directory"
    exit "$status"
}
trap cleanup EXIT
# Signatures establish artifact provenance; require the provider's asset and tag lock separately.
test "$(gh api "repos/$GITHUB_REPOSITORY/releases/tags/$RELEASE_TAG" --jq '.draft == false and .immutable == true')" = true
gh release download "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --dir "$directory"
python scripts/release/attest.py verify --directory "$directory" --tag "$RELEASE_TAG" --source "$SOURCE_SHA" --fingerprint "$COSIGN_PUBLIC_KEY_SHA256"
python scripts/release/verify-registry.py "$directory" "$RELEASE_TAG"
python scripts/ci/check-distribution.py "$directory"
