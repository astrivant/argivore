"""
Expose a runtime import marker solely inside the owned subprocess fixture.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

Path(os.environ["ARGIVORE_TEST_MARKER"]).write_text("selected")


def execute(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """
    Return a selected value without reparsing the process arguments.

    Args:
        args (argparse.Namespace): Typed leaf input.
        parser (argparse.ArgumentParser): Owning leaf parser.

    Returns:
        int: Selected exit status.
    """
    return int(args.value)
