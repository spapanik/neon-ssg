from __future__ import annotations

from pyutilkit.term import SGRCodes, SGRString

from neon_ssg.commands.build import BuildCommand
from neon_ssg.commands.serve import ServeCommand
from neon_ssg.lib.cli import CLIArgs, parse_args
from neon_ssg.lib.exceptions import NeonSSGError


def _run(args: CLIArgs) -> None:
    match args.subcommand:
        case "build":
            BuildCommand(verbosity=args.verbosity).run()
        case "serve":  # pragma: no branch
            ServeCommand(verbosity=args.verbosity, host=args.host, port=args.port).run()


def main() -> None:
    args = parse_args()
    try:
        _run(args)
    except NeonSSGError as exc:
        SGRString(
            exc, prefix="neon-ssg: ", is_error=True, params=(SGRCodes.RED,)
        ).print()
        raise SystemExit(exc.exit_code) from exc
