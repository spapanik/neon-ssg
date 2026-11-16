"""Internal entry point for a development preview build."""

from __future__ import annotations

import sys
from pathlib import Path

from neon_ssg.commands.build import BuildCommand


def main() -> None:
    BuildCommand(verbosity=0, site_root=Path(sys.argv[1])).run()


if __name__ == "__main__":
    main()
