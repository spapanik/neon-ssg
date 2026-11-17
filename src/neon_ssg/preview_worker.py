"""Internal entry point for a development preview build."""

from __future__ import annotations

import sys
from pathlib import Path

from pyutilkit.term import SGRString

from neon_ssg.commands.build import BuildCommand
from neon_ssg.lib.exceptions import NeonSSGError


def main() -> None:
    try:
        BuildCommand(verbosity=0, site_root=Path(sys.argv[1])).run()
    except NeonSSGError as exc:
        SGRString(exc, is_error=True).print()
        raise SystemExit(exc.exit_code) from exc


if __name__ == "__main__":
    main()
