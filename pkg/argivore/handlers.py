"""
Resolve only the selected handler after argparse has accepted the complete input.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from attrs import frozen

from argivore.errors import DefinitionError, DispatchError

if TYPE_CHECKING:
    import argparse

__all__ = ["Handler", "LazyHandler", "dispatch"]

_DESTINATION = "_argivore_binding"


@runtime_checkable
class Handler(Protocol):
    """
    Receive one parsed namespace and the parser that owns its selected command.
    """

    def __call__(self, args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
        """
        Execute a selected command without parsing arguments again.

        Args:
            args (argparse.Namespace): Complete parsed inputs, including ancestor options.
            parser (argparse.ArgumentParser): Selected leaf parser for usage and errors.

        Returns:
            int: Process exit status to preserve at the entrypoint.
        """
        ...


@frozen
class LazyHandler:
    """
    Refer to a module-level callable without importing its runtime during help.

    Attributes:
        module (str): Absolute Python module name, including normal package initialization.
        attribute (str): Module-level callable implementing Handler.
    """

    module: str
    attribute: str = "execute"

    def __attrs_post_init__(self) -> None:
        """
        Validate import syntax without resolving the referenced module.

        Returns:
            None: The declaration has an absolute module and attribute name.

        Raises:
            DefinitionError: A module component or attribute is not an identifier.
        """
        if not all(part.isidentifier() for part in self.module.split(".")) or not self.attribute.isidentifier():
            raise DefinitionError("LazyHandler requires an absolute module and a module-level attribute")

    def resolve(self) -> Handler:
        """
        Import and validate the selected callable at execution time.

        Returns:
            Handler: Runtime callable; its signature remains the application's typed contract.

        Raises:
            ImportError: The selected module or one of its dependencies cannot load.
            AttributeError: The named callable is missing.
            DispatchError: The selected attribute is not callable.
        """
        target: object = getattr(import_module(self.module), self.attribute)
        if not isinstance(target, Handler):
            raise DispatchError(f"{self.module}.{self.attribute} is not callable")
        return target


@frozen
class _Binding:
    """
    Keep mutable parser ownership in one parser instance rather than the command tree.

    Attributes:
        handler (Handler | LazyHandler): Execution declaration selected by this parser.
        parser (argparse.ArgumentParser): Parser owning the leaf's usage and validation errors.
    """

    handler: Handler | LazyHandler
    parser: argparse.ArgumentParser


def bind(parser: argparse.ArgumentParser, handler: Handler | LazyHandler) -> None:
    """
    Attach an opaque execution binding to a leaf parser's defaults.

    Args:
        parser (argparse.ArgumentParser): Fresh parser owned by one registered leaf.
        handler (Handler | LazyHandler): Selected execution declaration.

    Returns:
        None: Parsed namespaces retain the correct leaf and owning parser.
    """
    parser.set_defaults(**{_DESTINATION: _Binding(handler, parser)})


def dispatch(args: argparse.Namespace) -> int:
    """
    Execute the selected leaf from a namespace parsed exactly once by the caller.

    Args:
        args (argparse.Namespace): Namespace produced by an Argivore-populated parser.

    Returns:
        int: Unmodified handler exit status.

    Raises:
        DispatchError: The namespace lacks a binding or the handler returns a non-integer.
    """
    binding: object = getattr(args, _DESTINATION, None)
    if not isinstance(binding, _Binding):
        raise DispatchError("Parse with an Argivore command before dispatching")

    # Runtime loading happens after validation, including required child selection.
    handler = binding.handler.resolve() if isinstance(binding.handler, LazyHandler) else binding.handler
    result = handler(args, binding.parser)
    if type(result) is not int:
        raise DispatchError("Command handlers must return an integer exit status")
    return result
