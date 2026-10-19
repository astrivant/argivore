# Security policy

<!-- toc:start -->
**Table of contents**

- [Report a vulnerability privately](#report-a-vulnerability-privately)
- [Supported versions](#supported-versions)
- [Execution boundary](#execution-boundary)
<!-- toc:end -->

## Report a vulnerability privately

Use [GitHub private vulnerability reporting](https://github.com/astrivant/argivore/security/advisories/new)
to contact this repository's maintainers. Private reporting is enabled for Argivore.
Avoid public issues for unpatched vulnerabilities or sensitive reproduction details.

Include the affected version, Python version, minimal reproduction, expected and
observed behavior, impact, and any suggested mitigation. Remove credentials and
unrelated personal data. Maintainers will coordinate validation, remediation and
public disclosure through the private advisory. No response-time guarantee is made.

## Supported versions

The latest published Argivore release receives security fixes. During the initial
0.0.x series, upgrade to its newest patch; older patches do not have a separate
maintenance branch. Until v0.0.1 is published, main is development source.

## Execution boundary

Argument builders and handlers are trusted application code. Lazy handler references
import Python modules with their normal initialization effects. Argivore is not a
sandbox, credential broker or authorization layer. Validate untrusted inputs and
apply application policy before performing sensitive effects.
