"""
Distinguish invalid command declarations from invalid execution bindings.
"""

from __future__ import annotations

__all__ = ["DefinitionError", "DispatchError"]


class DefinitionError(ValueError):
    """
    Report ambiguous command ownership or conflicting sibling names.
    """


class DispatchError(TypeError):
    """
    Report a missing executable binding or an invalid handler contract.
    """
