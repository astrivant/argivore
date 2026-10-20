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

Publishing uses the Artifact Registry endpoints declared in
[Astrivant's registry contract](https://github.com/astrivant/astrivant/blob/55c4ebd6cd8ed75e92ce8ab92de8e35e33a769eb/docs/artifact-registry.md).
After provisioning and client acceptance, grant this repository the scoped
`ARTIFACT_REGISTRY_CREDENTIALS` secret and set `ARTIFACT_REGISTRY_ENABLED=true`.
The existing `pypi` environment retains its release approval restrictions; its name
does not select the registry. Enable GitHub release immutability before the first
publication. Same-repository
PRs and main builds publish development previews after their verification gates;
forks receive no registry credentials. Pre-provisioning previews may skip, while
release publication still requires working registry credentials.

Development versions encode the PR and pipeline, for example
`0.8.3a55.dev1234+build.1`; zero identifies a branch without a PR. Release tags
retain their normal versions. Both build paths transfer the exact tested archives
and their `artifact-provenance.json` receipt to publication. The pipeline uses the
pinned shared helper and its isolated, locked environment.

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
It publishes those same bytes to Artifact Registry, verifies registry hashes and an isolated
installation, then publishes the immutable GitHub release. A final acceptance job
downloads and verifies the complete asset set against the trusted fingerprint.

The release includes distributions, per-file `.sigstore.json` bundles,
`SHA256SUMS` and its bundle, `cosign.pub`, `public-key.sha256`, `SOURCE.json`, and the signed `artifact-provenance.json` receipt.
Check the actual release asset names when retrieving files. A bundled key alone
does not establish trust; compare its DER SHA-256 fingerprint to your independently
retained value. In a checkout of the released tag, install gh and Cosign, provide an authenticated
registry reader token as `TWINE_PASSWORD`, and use the shared helper from the pinned
Astrivant revision. Set `REGISTRY_PYTHON` to its isolated interpreter,
`REGISTRY_SCRIPT` to `scripts/ci/artifacts.py`, and `REGISTRY_INFRASTRUCTURE` to that
Astrivant checkout. GitHub Actions supplies these values through the pinned action.
Then verify the release:

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
