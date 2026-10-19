# Command composition

<!-- toc:start -->
**Table of contents**

- [Declaration and execution](#declaration-and-execution)
- [Local and shared options](#local-and-shared-options)
- [Runtime handlers](#runtime-handlers)
- [Reuse and standalone entrypoints](#reuse-and-standalone-entrypoints)
<!-- toc:end -->

Argivore accepts typed command declarations and creates fresh argparse objects
for each mount. Its public exports are `Command`, `Handler`, `LazyHandler`,
`dispatch`, `DefinitionError` and `DispatchError`.

## Declaration and execution

| Operation | Result |
| --- | --- |
| `Command(name, description, configure=None, handler=None, children=(), aliases=())` | Frozen command declaration with exactly one of a handler or nonempty children. |
| `command.with_aliases(*aliases)` | New declaration with replacement aliases. |
| `command.build_parser(prog=None)` | Fresh standalone parser; no lazy handler imports. |
| `command.populate(parser)` | Add this declaration to a caller-owned fresh parser. |
| `command.register(subcommands)` | Mount beneath a collection returned by `add_subparsers`. |
| `command.run(argv=None)` | Parse once, dispatch, and return the selected integer status. |
| `dispatch(namespace)` | Execute the leaf binding in a successfully parsed namespace. |
| `LazyHandler(module, attribute="execute")` | Absolute module and module-level callable reference. |

Use tuples for children and aliases. Names must be nonempty tokens without
whitespace or a leading hyphen. Names and aliases must be unique within a parent.
The declaration rejects missing execution ownership and collisions before parsing.
Depth is bounded by Python and argparse recursion limits, not a separate routing
implementation. `populate` expects a fresh parser and does not promise idempotence.

## Local and shared options

Argument builders accept `argparse.ArgumentParser` and return `None`. A root
builder can declare `--account`; a leaf builder can declare `--limit`. The syntax
is then `acme --account example jobs list --limit 10`. Argparse does not make a
parent option valid after a child command. Do not redeclare the same destination
on descendants: child defaults can overwrite explicit parent values.

Configure callbacks run when parsers are built, including help. Keep their imports
light and restrict them to parser declarations. Lazy handlers do not isolate eager
side effects in your package's `__init__.py` or the module defining the tree.

## Runtime handlers

A handler implements `Handler`: `(args: argparse.Namespace,
parser: argparse.ArgumentParser) -> int`. It receives all ancestor and local values
and the selected leaf's parser. Call `parser.error(message)` for a usage error
scoped to that command. Its normal `SystemExit(2)` remains visible to the caller.
Zero indicates success; applications should use conventional nonnegative process
exit codes when returning through a shell.

`LazyHandler` resolves only after successful parsing. Import and missing-attribute
errors propagate, so deployment mistakes are visible. A non-callable attribute or
a non-integer return raises `DispatchError`; booleans are not exit statuses.
Application exceptions propagate unchanged. Lazy dispatch is not an execution
sandbox: use trusted module references and ordinary application authorization.

## Reuse and standalone entrypoints

Mount a declaration with `subtree.register(parser.add_subparsers(required=True))`,
then call `dispatch(parser.parse_args(argv))`. For standalone use, call
`subtree.run(argv)` or `subtree.build_parser(prog="alternate-name")`.
Every mount has independent parser state; aliases are meaningful when mounted
under a parent. `build_parser` and all generated child parsers disable option
abbreviations. A caller-supplied parser retains its own root configuration.

Reserve `_argivore_binding` for dispatch metadata. Do not expose it as an option
or replace it in namespace defaults. Declarations are frozen, but application
callables can still capture mutable state; Argivore does not freeze that state.
