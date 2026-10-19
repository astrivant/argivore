"""
Provide a small runnable example of nested command composition.
"""

from __future__ import annotations

from importlib.metadata import version
from typing import TYPE_CHECKING

from argivore import Command

if TYPE_CHECKING:
    import argparse
    from collections.abc import Sequence

__all__ = ["main"]


def root_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Expose the installed distribution version without executing a demo.

    Args:
        parser (argparse.ArgumentParser): Root parser.

    Returns:
        None: A standard version action is registered.
    """
    parser.add_argument("--version", action="version", version=version("argivore"))


def greeting_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Declare the demo leaf's optional name.

    Args:
        parser (argparse.ArgumentParser): Greeting parser.

    Returns:
        None: The leaf owns its name option.
    """
    parser.add_argument("--name", default="world")


def greet(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """
    Print a greeting after the complete command path has been parsed.

    Args:
        args (argparse.Namespace): Parsed greeting name.
        parser (argparse.ArgumentParser): Selected leaf parser.

    Returns:
        int: Successful exit status.
    """
    print(f"Hello, {args.name}!")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """
    Run the installed command through the same public API used by applications.

    Args:
        argv (Sequence[str] | None): Explicit tokens or process arguments.

    Returns:
        int: Demo handler exit status.
    """
    tree = Command(
        "argivore",
        "Compose argparse commands without manual routing.",
        configure=root_arguments,
        children=(Command("demo", "Run an example", children=(Command("greet", "Print a greeting", greeting_arguments, greet),)),),
    )
    return tree.run(argv)
