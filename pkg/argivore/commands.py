"""
Compose immutable declarations into fresh argparse parsers at every tree depth.
"""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING, Protocol

from attrs import evolve, frozen

from argivore.errors import DefinitionError
from argivore.handlers import Handler, LazyHandler, bind, dispatch

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

__all__ = ["Command"]


class _Subcommands(Protocol):
    """
    Use the public add_parser operation without depending on argparse's private type.
    """

    def add_parser(self, name: str, *, aliases: Sequence[str], help: str, description: str, allow_abbrev: bool) -> argparse.ArgumentParser:
        """
        Create a child parser within the caller's subcommand collection.

        Args:
            name (str): Canonical command token.
            aliases (Sequence[str]): Alternative tokens at this parent.
            help (str): Parent help summary.
            description (str): Child help description.
            allow_abbrev (bool): Whether partial option spellings are accepted.

        Returns:
            argparse.ArgumentParser: Fresh child parser.
        """
        ...


@frozen
class Command:
    """
    Describe either a group of commands or one executable leaf.

    Attributes:
        name (str): Canonical token when mounted beneath another command.
        description (str): Description used in both parent and local help.
        configure (Callable[[argparse.ArgumentParser], None] | None): Local option declarations, run once per fresh parser.
        handler (Handler | LazyHandler | None): Leaf callable or deferred runtime reference.
        children (tuple[Command, ...]): Required child selection for a group.
        aliases (tuple[str, ...]): Alternative names when mounted beneath a parent.
    """

    name: str
    description: str
    configure: Callable[[argparse.ArgumentParser], None] | None = None
    handler: Handler | LazyHandler | None = None
    children: tuple[Command, ...] = ()
    aliases: tuple[str, ...] = ()

    def __attrs_post_init__(self) -> None:
        """
        Reject missing execution ownership and ambiguous sibling selection.

        Returns:
            None: The immutable declaration can be mounted without name conflicts.

        Raises:
            DefinitionError: Tokens are invalid, ownership is ambiguous, or siblings overlap.
        """
        if (self.handler is None) == (not self.children):
            raise DefinitionError("A command needs either a handler or children, exclusively")
        tokens = (self.name, *self.aliases)
        if any(not token or token.startswith("-") or any(character.isspace() for character in token) for token in tokens):
            raise DefinitionError("Command names and aliases must be nonempty tokens, without whitespace or a leading hyphen")
        if len(set(tokens)) != len(tokens):
            raise DefinitionError("A command cannot repeat its name or aliases")

        # Include aliases in the sibling namespace so registration never silently changes routing.
        sibling_tokens = [token for child in self.children for token in (child.name, *child.aliases)]
        if len(set(sibling_tokens)) != len(sibling_tokens):
            raise DefinitionError("Sibling command names and aliases must be unique")

    def with_aliases(self, *aliases: str) -> Command:
        """
        Return a reusable declaration with replacement aliases.

        Args:
            *aliases (str): Alternative tokens at the next mount point.

        Returns:
            Command: New declaration; the original is unchanged.
        """
        return evolve(self, aliases=aliases)

    def register(self, subcommands: _Subcommands) -> None:
        """
        Mount this declaration and all descendants under an existing group.

        Args:
            subcommands (_Subcommands): Collection returned by ArgumentParser.add_subparsers.

        Returns:
            None: A fresh subtree is registered without loading leaf runtimes.
        """
        child = subcommands.add_parser(
            self.name, aliases=self.aliases, help=self.description, description=self.description, allow_abbrev=False
        )
        self.populate(child)

    def populate(self, parser: argparse.ArgumentParser) -> None:
        """
        Apply the declaration to a caller-owned fresh parser.

        Args:
            parser (argparse.ArgumentParser): Parser for custom formatting or standalone use.

        Returns:
            None: Local arguments and required descendants or leaf execution are registered.
        """
        if self.configure is not None:
            self.configure(parser)
        if self.handler is not None:
            bind(parser, self.handler)
            return

        # No shared selection destination is needed: the leaf binding determines dispatch.
        subcommands = parser.add_subparsers(required=True)
        for child in self.children:
            child.register(subcommands)

    def build_parser(self, *, prog: str | None = None) -> argparse.ArgumentParser:
        """
        Build an independent parser with unambiguous option spellings.

        Args:
            prog (str | None): Displayed entrypoint, defaulting to this command's name.

        Returns:
            argparse.ArgumentParser: Fresh parser; runtime handlers remain unloaded.
        """
        parser = argparse.ArgumentParser(prog=prog or self.name, description=self.description, allow_abbrev=False)
        self.populate(parser)
        return parser

    def run(self, argv: Sequence[str] | None = None) -> int:
        """
        Parse once and dispatch the selected leaf using normal argparse exit behavior.

        Args:
            argv (Sequence[str] | None): Explicit tokens, or the process arguments when omitted.

        Returns:
            int: Selected handler's exit status.

        Raises:
            SystemExit: Argparse displays help or rejects invalid input.
        """
        return dispatch(self.build_parser().parse_args(argv))
