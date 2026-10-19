"""
Build reusable argparse command trees with explicit execution ownership.
"""

from __future__ import annotations

from argivore.commands import Command
from argivore.errors import DefinitionError, DispatchError
from argivore.handlers import Handler, LazyHandler, dispatch

__all__ = ["Command", "DefinitionError", "DispatchError", "Handler", "LazyHandler", "dispatch"]
