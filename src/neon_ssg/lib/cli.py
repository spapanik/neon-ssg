import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from typing import Literal

from neon_ssg.__version__ import __version__

sys.tracebacklimit = 0


@dataclass(frozen=True, slots=True)
class CLIArgs:
    subcommand: Literal["build", "serve"]
    verbosity: int
    host: str = "127.0.0.1"
    port: int = 8000


def parse_args() -> CLIArgs:
    parser = ArgumentParser(prog="ssg", description="Static site generator")
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="print the version and exit",
    )

    parent_parser = ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbosity",
        help="increase the level of verbosity",
    )

    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    subparsers.add_parser(
        "build", parents=[parent_parser], help="build the static site"
    )
    serve_parser = subparsers.add_parser(
        "serve", parents=[parent_parser], help="build and serve the static site"
    )
    serve_parser.add_argument(
        "--host", default="127.0.0.1", help="host interface to bind"
    )
    serve_parser.add_argument(
        "--port", default=8000, type=int, help="port to listen on"
    )

    args = parser.parse_args()
    if args.verbosity > 0:
        sys.tracebacklimit = 1000

    return CLIArgs(
        subcommand=args.subcommand,
        verbosity=args.verbosity,
        host=getattr(args, "host", "127.0.0.1"),
        port=getattr(args, "port", 8000),
    )
