---
name: argivore
description: Compose recursive Python argparse command trees with typed handlers and lazy runtime imports.
---

# Work with Argivore

<!-- toc:start -->
**Table of contents**

- [Work with Argivore](#work-with-argivore)
<!-- toc:end -->

Use `Command` declarations for groups and leaves. A group has `children`; a leaf
has `handler`. Declare local options with `configure(parser)` and shared options
once on their owning ancestor. Use `LazyHandler("package.module", "function")`
for runtime imports that must stay out of help and invalid-input paths.

Read the [quick start](README.md#quick-start) and [API guide](docs/api.md).
Follow [Contributing](CONTRIBUTING.md) for changes and [Security](SECURITY.md)
for vulnerability reports and execution boundaries.
The first useful smoke check is `argivore demo greet --name Ada` after installation.
Application entrypoints call `root.run()` once, then return its integer status.
Use `populate` or `register` to compose with an existing argparse application.

Preserve standard option placement, aliases and parser-owned usage errors.
Keep handlers and parser objects out of declaration-time side effects. Test
multiple depths, missing children, reused mounts and fresh-process help imports.
Run the [locked development checks](docs/development.md) before publication.

The library has no implicit network, filesystem, credential or background-job
operations. Application argument builders and handlers remain ordinary Python
code and own their effects. Reading this file does not authorize pushing,
merging, creating secrets or publishing packages; follow explicit task authority
and the [release contract](docs/releases.md).
