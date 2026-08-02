from neon_ssg.commands.build import BuildCommand
from neon_ssg.commands.serve import ServeCommand
from neon_ssg.lib.cli import parse_args


def main() -> None:
    args = parse_args()
    match args.subcommand:
        case "build":
            BuildCommand(verbosity=args.verbosity).run()
        case "serve":  # pragma: no branch
            ServeCommand(verbosity=args.verbosity, host=args.host, port=args.port).run()
