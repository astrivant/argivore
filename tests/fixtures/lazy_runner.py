"""
Exercise lazy selection in a fresh interpreter without importing either leaf runtime.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from argivore import Command, LazyHandler

if TYPE_CHECKING:
    import argparse


def value(parser: argparse.ArgumentParser) -> None:
    """
    Declare the leaf input without importing its runtime or test frameworks.

    Args:
        parser (argparse.ArgumentParser): Leaf parser.

    Returns:
        None: The parser accepts one required integer.
    """
    parser.add_argument("--value", type=int, required=True)


tree = Command(
    "fresh",
    "Fresh interpreter fixture",
    children=(
        Command(
            "group",
            "Select",
            children=(
                Command("run", "Selected", value, LazyHandler("tests.fixtures.lazy_runtime")),
                Command("unselected", "Never imported", handler=LazyHandler("missing_unselected_runtime")),
            ),
        ),
    ),
)
raise SystemExit(tree.run())
