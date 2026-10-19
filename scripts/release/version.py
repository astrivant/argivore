"""
Derive distribution metadata from an immutable, stable release tag.
"""

from __future__ import annotations

import re
import subprocess
import sys


def main(tag: str) -> int:
    """
    Stamp the source manifest before building the tagged artifact.

    Args:
        tag (str): Explicit vMAJOR.MINOR.PATCH release tag.

    Returns:
        int: Zero after Poetry accepts the release version.

    Raises:
        ValueError: The tag is not a stable release identifier.
    """
    if re.fullmatch(r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", tag) is None:
        raise ValueError("Expected a stable vMAJOR.MINOR.PATCH tag")
    subprocess.run(["poetry", "version", tag[1:]], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
