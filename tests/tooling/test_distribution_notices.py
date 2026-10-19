"""
Reject missing or altered attribution before installing any release artifact.
"""

from __future__ import annotations

import io
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("kind", ["wheel", "source"])
@pytest.mark.parametrize("notice", ["LICENSE", "NOTICE"])
@pytest.mark.parametrize("damage", ["missing", "changed"])
def test_distribution_rejects_notice_damage(tmp_path: Path, kind: str, notice: str, damage: str) -> None:
    """
    Exercise real archive readers without reaching dependency downloads or installation.

    Args:
        tmp_path (Path): Disposable artifact directory.
        kind (str): Distribution format with damaged attribution.
        notice (str): Required license or attribution member.
        damage (str): Missing member or changed bytes.

    Returns:
        None: The distribution verifier rejects the damaged notice with a specific diagnostic.
    """
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    metadata = (
        f"Metadata-Version: 2.4\nName: argivore\nVersion: {version}\nRequires-Dist: attrs (>=26.1,<27)\n"
        "License-Expression: Apache-2.0\nLicense-File: LICENSE\nLicense-File: NOTICE\n"
    ).encode()
    notices = {name: (ROOT / name).read_bytes() for name in ("LICENSE", "NOTICE")}
    wheel_files = {f"argivore-{version}.dist-info/METADATA": metadata, "argivore/py.typed": b""}
    source_files = {f"argivore-{version}/PKG-INFO": metadata}

    # Damage only the selected format so the verifier reaches the intended boundary.
    for format_name, files, prefix in (
        ("wheel", wheel_files, f"argivore-{version}.dist-info/licenses"),
        ("source", source_files, f"argivore-{version}"),
    ):
        for name, content in notices.items():
            if format_name == kind and name == notice:
                if damage == "missing":
                    continue
                content = b"changed attribution"
            files[f"{prefix}/{name}"] = content
    with zipfile.ZipFile(tmp_path / f"argivore-{version}-py3-none-any.whl", "w") as wheel:
        for name, content in wheel_files.items():
            wheel.writestr(name, content)
    with tarfile.open(tmp_path / f"argivore-{version}.tar.gz", "w:gz") as source:
        for name, content in source_files.items():
            member = tarfile.TarInfo(name)
            member.size = len(content)
            source.addfile(member, io.BytesIO(content))
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/ci/check-distribution.py"), str(tmp_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    label = "Wheel" if kind == "wheel" else "Source archive"
    assert f"{label} {notice}" in result.stderr
