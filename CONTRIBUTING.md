# Contributing

<!-- toc:start -->
**Table of contents**

- [Setup and checks](#setup-and-checks)
- [Implementation and review](#implementation-and-review)
<!-- toc:end -->

Discuss a bug or proposed feature in an issue, then open a focused PR against main.
Describe the behavior, why it matters and the checks you ran. Report vulnerabilities
through the private channel in [SECURITY.md](SECURITY.md).

## Setup and checks

Follow the [development guide](docs/development.md) for supported Python, Poetry,
Node and Cosign versions, locked installation, hooks, tests and clean package checks.
Do not re-resolve dependencies during ordinary validation. Update manifests and
lockfiles together when changing dependencies.

Before review, run `poetry run pre-commit run --all-files`,
`poetry run pytest -n 2 --cov`, and `npm test --prefix scripts/documentation`.
For packaging changes, also build, check metadata and run the isolated distribution
verification commands in the development guide. Review and stage generated README
contents and CODEOWNERS changes explicitly.

## Implementation and review

Keep runtime code in `pkg/argivore/`, feature tests in `tests/`, repository tools in
`scripts/`, and detailed guides in `docs/`. Preserve typed public contracts, Google
docstrings, lazy import boundaries and ordinary argparse behavior. Add regressions
for behavior changes, including fresh-process help checks when imports change.

Required CI and code-owner review gate main. Commits and release tags are signed;
the [release guide](docs/releases.md) describes the separately authorized publication
and signing setup. Contributor tests and ordinary PRs do not publish packages.

Contributions to Argivore's runtime use [Apache-2.0](LICENSE). Preserve [NOTICE](NOTICE)
and the separate [development-helper notices](scripts/NOTICE.md) when adapting those
files. Check source-level terms before copying code into the package.
