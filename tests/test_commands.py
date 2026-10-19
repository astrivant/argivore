"""
Exercise recursive composition through observable argparse behavior.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest
from attrs.exceptions import FrozenInstanceError
from hypothesis import given
from hypothesis import strategies as st

from argivore import Command, DefinitionError, DispatchError, LazyHandler, dispatch
from argivore.cli import main

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import CaptureFixture, MonkeyPatch


def options(parser: argparse.ArgumentParser) -> None:
    """
    Put shared inputs on their owning ancestor.

    Args:
        parser (argparse.ArgumentParser): Parent parser.

    Returns:
        None: The shared account has one declaration.
    """
    parser.add_argument("--account", default="default")


def value(parser: argparse.ArgumentParser) -> None:
    """
    Declare a required typed input on the executable leaf.

    Args:
        parser (argparse.ArgumentParser): Leaf parser.

    Returns:
        None: The leaf requires an integer.
    """
    parser.add_argument("--value", type=int, required=True)


def execute(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """
    Expose selection and parent-option preservation through the exit value.

    Args:
        args (argparse.Namespace): Parsed inputs.
        parser (argparse.ArgumentParser): Selected parser.

    Returns:
        int: Selected input, including a distinctive offset for the selected account.
    """
    assert parser.prog.endswith(("run", "go"))
    assert args.account == "chosen"
    return int(args.value)


def tree(depth: int) -> tuple[Command, list[str]]:
    """
    Build independently reusable command declarations at several depths.

    Args:
        depth (int): Number of intermediate groups.

    Returns:
        tuple[Command, list[str]]: Root and canonical leaf-selection tokens.
    """
    selected = Command("run", "Run a value", value, execute).with_aliases("go")
    path = ["run"]
    for index in range(depth):
        selected = Command(f"group{index}", "Choose an operation", children=(selected,))
        path.insert(0, selected.name)
    return Command("demo", "Select a command", options, children=(selected,)), path


@given(depth=st.integers(0, 8), number=st.integers(-1000, 1000), alias=st.booleans())
def test_recursive_replay_preserves_inputs(depth: int, number: int, alias: bool) -> None:
    """
    Preserve caller tokens, ancestor values and deterministic selection at generated depths.

    Args:
        depth (int): Intermediate groups.
        number (int): Selected integer result.
        alias (bool): Whether to select the leaf through its alias.

    Returns:
        None: Repeated fresh parsers choose the same leaf without mutating inputs.
    """
    root, path = tree(depth)
    tokens = ["--account", "chosen", *path[:-1], "go" if alias else "run", "--value", str(number)]
    original = tokens.copy()
    assert root.run(tokens) == number
    assert root.run(tokens) == number
    assert tokens == original


def test_reused_subtree_has_independent_parser_ownership() -> None:
    """
    Mount the same declaration under separate names without storing mutable parsers in it.

    Returns:
        None: Standalone and nested use select distinct parsers with the same behavior.
    """
    root, path = tree(2)
    standalone = root.build_parser(prog="standalone")
    mounted = argparse.ArgumentParser(prog="host")
    root.register(mounted.add_subparsers(required=True))
    assert dispatch(standalone.parse_args(["--account", "chosen", *path, "--value", "13"])) == 13
    assert dispatch(mounted.parse_args(["demo", "--account", "chosen", *path, "--value", "29"])) == 29
    assert standalone is not mounted
    with pytest.raises(FrozenInstanceError):
        root.__setattr__("name", "changed")
    assert root.aliases == () and root.with_aliases("alternate").aliases == ("alternate",)


@pytest.mark.parametrize("prefix", [[], ["group1"], ["group1", "group0"], ["group1", "group0", "run"]])
def test_help_and_invalid_inputs_at_every_level(prefix: list[str], capsys: CaptureFixture[str]) -> None:
    """
    Use argparse's normal help and error exits at every command tier.

    Args:
        prefix (list[str]): Partial or complete command path.
        capsys (CaptureFixture[str]): Captured parser output.

    Returns:
        None: Help exits zero and missing or invalid inputs exit two.
    """
    root, _ = tree(2)
    with pytest.raises(SystemExit) as help_exit:
        root.run([*prefix, "--help"])
    assert help_exit.value.code == 0
    assert "usage:" in capsys.readouterr().out
    with pytest.raises(SystemExit) as error_exit:
        root.run([*prefix, "--unknown"])
    assert error_exit.value.code == 2
    assert "error:" in capsys.readouterr().err


def test_option_abbreviations_and_ancestor_placement_are_explicit() -> None:
    """
    Reject partial option spellings and options placed after their owning command.

    Returns:
        None: Option placement remains the standard argparse contract.
    """
    root, _ = tree(0)
    for arguments in (["--acc", "chosen", "run", "--value", "1"], ["run", "--account", "chosen", "--value", "1"]):
        with pytest.raises(SystemExit) as result:
            root.run(arguments)
        assert result.value.code == 2


@pytest.mark.parametrize("name", ["", "two words", "-option", "line\nfeed"])
def test_invalid_command_tokens_fail_before_registration(name: str) -> None:
    """
    Keep invalid command definitions out of argparse registration.

    Args:
        name (str): Invalid token.

    Returns:
        None: The declaration raises a domain-specific diagnostic.
    """
    with pytest.raises(DefinitionError, match="tokens"):
        Command(name, "Invalid", handler=execute)


def test_ambiguous_ownership_and_collisions_are_rejected() -> None:
    """
    Reject incomplete leaves, mixed groups and alias collisions before parser creation.

    Returns:
        None: Every ambiguous declaration is rejected.
    """
    leaf = Command("run", "Execute", handler=execute)
    with pytest.raises(DefinitionError, match="exclusively"):
        Command("empty", "Empty")
    with pytest.raises(DefinitionError, match="exclusively"):
        Command("mixed", "Mixed", handler=execute, children=(leaf,))
    with pytest.raises(DefinitionError, match="repeat"):
        leaf.with_aliases("run")
    with pytest.raises(DefinitionError, match="Sibling"):
        Command("root", "Root", children=(leaf, leaf.with_aliases("other")))
    with pytest.raises(DefinitionError, match="Sibling"):
        Command("root", "Root", children=(leaf.with_aliases("go"), Command("go", "Collision", handler=execute)))
    with pytest.raises(DispatchError, match="before dispatching"):
        dispatch(argparse.Namespace())


@pytest.mark.parametrize("module,attribute", [("", "execute"), (".relative", "execute"), ("valid", "nested.method")])
def test_lazy_reference_syntax_is_validated(module: str, attribute: str) -> None:
    """
    Validate import declarations without loading optional runtimes.

    Args:
        module (str): Candidate module.
        attribute (str): Candidate module-level attribute.

    Returns:
        None: Unsupported references fail at declaration time.
    """
    with pytest.raises(DefinitionError):
        LazyHandler(module, attribute)


@pytest.mark.parametrize("invalid_result", ["invalid", True, None])
def test_lazy_contract_and_runtime_failures_remain_visible(monkeypatch: MonkeyPatch, invalid_result: object) -> None:
    """
    Fail clearly for non-callable runtime attributes and invalid handler results.

    Args:
        monkeypatch (MonkeyPatch): Replace a known attribute with invalid synthetic values.
        invalid_result (object): Unsupported handler return value.

    Returns:
        None: Import failures and execution contract failures are not hidden.
    """
    with pytest.raises(ImportError):
        LazyHandler("argivore_missing_runtime").resolve()
    with pytest.raises(AttributeError):
        LazyHandler("argivore", "missing_runtime").resolve()
    with pytest.raises(DispatchError, match="not callable"):
        LazyHandler("argivore", "__all__").resolve()
    monkeypatch.setattr("argivore.cli.greet", lambda args, parser: invalid_result)
    with pytest.raises(DispatchError, match="integer exit status"):
        Command("run", "Invalid result", handler=LazyHandler("argivore.cli", "greet")).run([])


def reject(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """
    Report an application validation failure through the owning parser.

    Args:
        args (argparse.Namespace): Parsed synthetic inputs.
        parser (argparse.ArgumentParser): Selected leaf parser.

    Returns:
        int: Unreachable because the parser exits on invalid input.

    Raises:
        SystemExit: The selected command reports a usage error.
    """
    parser.error("rejected by the selected runtime")


def test_runtime_error_usage_belongs_to_selected_leaf(capsys: CaptureFixture[str]) -> None:
    """
    Preserve the leaf's usage path when application validation rejects input.

    Args:
        capsys (CaptureFixture[str]): Captured argparse diagnostic.

    Returns:
        None: The error identifies the complete selected command path.
    """
    root = Command("service", "Service", children=(Command("jobs", "Jobs", children=(Command("run", "Run", handler=reject),)),))
    with pytest.raises(SystemExit) as result:
        root.run(["jobs", "run"])
    assert result.value.code == 2
    assert "usage: service jobs run" in capsys.readouterr().err


def test_cli_and_module_entrypoints_match(capsys: CaptureFixture[str], monkeypatch: MonkeyPatch) -> None:
    """
    Share the installed console behavior with explicit and process argument lists.

    Args:
        capsys (CaptureFixture[str]): Captured greeting.
        monkeypatch (MonkeyPatch): Supply process arguments without mutating callers.

    Returns:
        None: Both entrypoints display the documented result.
    """
    assert main(["demo", "greet", "--name", "Ada"]) == 0
    assert capsys.readouterr().out == "Hello, Ada!\n"
    monkeypatch.setattr(sys, "argv", ["argivore", "demo", "greet"])
    assert main() == 0
    assert capsys.readouterr().out == "Hello, world!\n"
    result = subprocess.run([sys.executable, "-m", "argivore", "--version"], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "0.0.1"


@pytest.mark.parametrize(
    "tokens,status",
    [
        (["--help"], 0),
        (["group", "--help"], 0),
        (["group", "run", "--help"], 0),
        ([], 2),
        (["group", "run"], 2),
        (["group", "run", "--value", "7"], 7),
    ],
)
def test_help_does_not_import_runtime_in_fresh_process(tokens: list[str], status: int, tmp_path: Path) -> None:
    """
    Observe runtime import effects in a fresh interpreter for each parser operation.

    Args:
        tokens (list[str]): Command tokens for help, error or execution.
        status (int): Expected process result.
        tmp_path (Path): Owned side-effect marker directory.

    Returns:
        None: Only valid execution imports the selected runtime module.
    """
    marker = tmp_path / "imported"
    environment = dict(os.environ, ARGIVORE_TEST_MARKER=str(marker))
    result = subprocess.run([sys.executable, "-m", "tests.fixtures.lazy_runner", *tokens], env=environment, capture_output=True, text=True)
    assert result.returncode == status, result.stderr
    assert marker.exists() == (status == 7)
