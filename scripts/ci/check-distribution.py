"""
Verify package membership and exercise the installed CLI outside the source checkout.
"""

from __future__ import annotations

import email.parser
import os
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import venv
import zipfile
from pathlib import Path


def locked_requirement(lock: Path) -> str:
    """
    Select the single locked runtime dependency without importing an installed copy.

    Args:
        lock (Path): Committed Poetry lockfile belonging to the checked source.

    Returns:
        str: Pinned pip requirement with the lockfile's accepted artifact hashes.

    Raises:
        ValueError: The dependency is absent, ambiguous or lacks complete hash metadata.
    """
    packages = tomllib.loads(lock.read_text()).get("package", [])
    matches = [item for item in packages if item.get("name") == "attrs"]
    if len(matches) != 1:
        raise ValueError("Expected one locked attrs version")
    package = matches[0]
    version = package.get("version")
    hashes = [item.get("hash") for item in package.get("files", [])]
    if not isinstance(version, str) or not hashes or any(not isinstance(value, str) or not value.startswith("sha256:") for value in hashes):
        raise ValueError("Locked attrs version or hashes are missing")
    return f"attrs=={version} " + " ".join(f"--hash={value}" for value in hashes) + "\n"


def verify(directory: Path) -> None:
    """
    Install the built wheel with the exact runtime dependency from the committed lockfile.

    Args:
        directory (Path): Directory containing one wheel and one source archive.

    Returns:
        None: Package metadata, installed imports and CLI behavior satisfy the extraction contract.

    Raises:
        ValueError: Distribution membership or metadata differs from the expected package.
    """
    wheels = list(directory.glob("*.whl"))
    sources = list(directory.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sources) != 1:
        raise ValueError("Expected exactly one wheel and one source archive")
    wheel = wheels[0].resolve()
    expected = (
        os.environ.get("RELEASE_TAG", "").removeprefix("v") or tomllib.loads(Path("pyproject.toml").read_text())["project"]["version"]
    )
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        metadata = email.parser.BytesParser().parsebytes(archive.read(next(name for name in names if name.endswith("/METADATA"))))
        dependencies = metadata.get_all("Requires-Dist", [])
        if metadata["Name"] != "argivore" or metadata["Version"] != expected or dependencies != ["attrs (>=26.1,<27)"]:
            raise ValueError("Unexpected package identity or runtime dependencies")
        if any(name.startswith(("tests/", "scripts/")) for name in names) or "argivore/py.typed" not in names:
            raise ValueError("Development code leaked or type metadata is missing")
        if metadata["License-Expression"] != "Apache-2.0":
            raise ValueError("Runtime license metadata differs from the approved terms")

        # Attribution is part of the distribution contract, independent of the release source revision.
        if set(metadata.get_all("License-File", [])) != {"LICENSE", "NOTICE"}:
            raise ValueError("Wheel license-file declarations are incomplete")
        for notice in ("LICENSE", "NOTICE"):
            matches = [name for name in names if name.endswith(f".dist-info/licenses/{notice}")]
            if len(matches) != 1 or archive.read(matches[0]) != Path(notice).read_bytes():
                raise ValueError(f"Wheel {notice} is missing or differs from the source")
    with tarfile.open(sources[0]) as source:
        members = [member for member in source.getmembers() if member.name.endswith("/PKG-INFO")]
        if len(members) != 1:
            raise ValueError("Expected source archive metadata")
        stream = source.extractfile(members[0])
        if stream is None:
            raise ValueError("Source metadata is not a regular file")
        metadata = email.parser.BytesParser().parsebytes(stream.read())
        if metadata["Name"] != "argivore" or metadata["Version"] != expected:
            raise ValueError("Source archive and wheel versions differ")

        # Verify actual archive members rather than relying on manifest inclusion settings.
        names = source.getnames()
        for notice in ("LICENSE", "NOTICE"):
            name = f"argivore-{expected}/{notice}"
            if names.count(name) != 1 or not source.getmember(name).isfile():
                raise ValueError(f"Source archive {notice} is missing or not a regular file")
            content = source.extractfile(name)
            if content is None or content.read() != Path(notice).read_bytes():
                raise ValueError(f"Source archive {notice} differs from the source")
    with tempfile.TemporaryDirectory(prefix="argivore-wheel-") as temporary:
        root = Path(temporary)
        environment = {
            key: value for key, value in os.environ.items() if key not in {"PYTHONPATH", "VIRTUAL_ENV"} and not key.startswith("GIT_")
        }
        environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
        venv.EnvBuilder(with_pip=True).create(root / "environment")
        binaries = root / "environment" / ("Scripts" if os.name == "nt" else "bin")
        python = binaries / ("python.exe" if os.name == "nt" else "python")
        # A clean acceptance runner has no application dependencies installed. Bind downloads to source and hashes.
        requirements = root / "requirements.txt"
        requirements.write_text(locked_requirement(Path("poetry.lock")))
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "download",
                "--no-deps",
                "--only-binary=:all:",
                "--dest",
                str(root),
                "--require-hashes",
                "--requirement",
                str(requirements),
            ],
            check=True,
        )
        subprocess.run(
            [str(python), "-m", "pip", "install", "--no-index", "--find-links", str(root), str(wheel)],
            cwd=root,
            env=environment,
            check=True,
        )
        command = binaries / ("argivore.exe" if os.name == "nt" else "argivore")
        subprocess.run([str(command), "--help"], cwd=root, env=environment, check=True, capture_output=True)
        result = subprocess.run(
            [str(command), "demo", "greet", "--name", "installed"], cwd=root, env=environment, check=True, capture_output=True, text=True
        )
        if result.stdout != "Hello, installed!\n":
            raise ValueError("Installed command tree differs from the documented example")


if __name__ == "__main__":
    verify(Path(sys.argv[1]))
