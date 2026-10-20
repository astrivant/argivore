# Signed releases

<!-- toc:start -->
**Table of contents**

- [Repository setup](#repository-setup)
- [Publication and verification](#publication-and-verification)
<!-- toc:end -->

The initial package version is 0.0.1. A signed `v*` tag on reviewed main triggers
the CI workflow. Source checks, the Python matrix and clean-distribution checks
must pass before publication. Tag jobs build the immutable tagged source and derive
the distribution version from that tag.

## Repository setup

The existing organization `PYPI_API_TOKEN` must grant this repository access.
Only the tag publisher receives it. Configure the `pypi` environment and enable
GitHub release immutability before the first publication.

After explicit authorization, create or reuse this repository's signing identity:

```bash
bash scripts/release/setup-signing.sh --repo astrivant/argivore
```

The helper supports `--help` and `--key-dir`, requires gh, OpenSSL and Cosign, and
uploads `COSIGN_PRIVATE_KEY`, `COSIGN_PASSWORD` and the public fingerprint variable
`COSIGN_PUBLIC_KEY_SHA256`. It retains a private local backup, rejects partial key
sets, and does not rotate an existing complete identity. Keep that backup outside
Git. Store its printed public fingerprint separately as the trust anchor.

## Publication and verification

The workflow verifies the signed source tag, creates a draft release, signs the
final wheel and source archive with Cosign, and verifies checksums and signatures.
It publishes those same bytes to PyPI, verifies registry hashes and an isolated
installation, then publishes the immutable GitHub release. A final acceptance job
downloads and verifies the complete asset set against the trusted fingerprint.

The release includes distributions, per-file `.sigstore.json` bundles,
`SHA256SUMS` and its bundle, `cosign.pub`, `public-key.sha256`, and `SOURCE.json`.
Check the actual release asset names when retrieving files. A bundled key alone
does not establish trust; compare its DER SHA-256 fingerprint to your independently
retained value. In a checkout of the released tag, with gh and Cosign installed:

```bash
export RELEASE_TAG=v0.0.1
export GITHUB_REPOSITORY=astrivant/argivore
export SOURCE_SHA="$(git rev-parse "$RELEASE_TAG^{commit}")"
export COSIGN_PUBLIC_KEY_SHA256='YOUR_INDEPENDENTLY_TRUSTED_FINGERPRINT'
bash scripts/release/verify-published.sh
```

Retries preserve the signing identity and reject conflicting already-published
bytes. Missing registry files have bounded retry; changed or yanked files fail.
After acceptance, contributor feedback links included PRs to their version.
Maintainers listed in `.github/release-notes.json` are excluded from new-contributor
messaging, and one classified What changed section describes the release.

Triggering a tag pipeline is not confirmation of a published package. Check the
workflow's release acceptance and actual registry artifacts before adopting it.
