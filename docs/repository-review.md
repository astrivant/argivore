# Initial repository review

<!-- toc:start -->
**Table of contents**

- [Initial repository review](#initial-repository-review)
<!-- toc:end -->

The initial delivery covers the Python library, installed demonstration command,
documentation, package boundaries, local hooks, CI and release automation.

| Surface | Evidence and acceptance boundary |
| --- | --- |
| Recursive parser behavior | Property tests cover nested groups, aliases, parent options, deterministic replay and unchanged caller inputs. |
| Import and error ownership | Fresh-process tests distinguish help, invalid selection and selected runtime execution; handlers receive their leaf parser. |
| Public package | Strict typing, Google docstrings, explicit exports and `py.typed`; built wheel and source notices are checked before isolated installation. |
| Dependencies | Python and JavaScript tools use committed locks; Actions use reviewed commit pins; weekly updates retain review. |
| Documentation | Generated README contents, Markdown, Mermaid and math checks run locally and in CI. |
| Project policies | Root CONTRIBUTING.md links the actual development and review workflow; SECURITY.md names the verified private reporting channel and supported versions. |
| CI | Independent checks, tests and builds join at Required CI; generated repair uses trusted base code with an allowlist. |
| Coverage | Runtime branch coverage has a 95% floor; main publishes measured line coverage with source and report digests. |
| Publication | Signed tags, verified draft assets, PyPI byte agreement, independently trusted key fingerprint and immutable release acceptance. |
| Host settings | Settings catalog requests Required CI and owner review; actual enforcement must be verified through the provider API. |

This package owns no servers, subprocess supervisor, thread pool, datastore,
containers or Helm charts. Service lifecycle, cluster matrix and deployment checks
therefore do not apply to its runtime. Application callbacks own their own effects.
No existing consumers are migrated in the initial release.

Local test results and hosted results belong to the exact PR revision. The PR
records those observations separately. Initial coverage publication, registry
availability and release acceptance remain pending until their corresponding
main or tag workflows complete. Passing tests establish the exercised contracts,
not a proof of correctness for all possible application callbacks.
