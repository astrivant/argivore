"""
Share the installed console entrypoint with python -m argivore.
"""

from __future__ import annotations

from argivore.cli import main

raise SystemExit(main())
