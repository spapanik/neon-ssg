from __future__ import annotations

import sys
from unittest import mock

import pytest

from neon_ssg.__version__ import __version__
from neon_ssg.lib.cli import parse_args


@mock.patch.object(sys, "argv", new=["ssg", "build"])
def test_build_uses_defaults() -> None:
    args = parse_args()

    assert args.subcommand == "build"
    assert args.verbosity == 0


@mock.patch.object(sys, "argv", new=["ssg", "build"])
def test_build_reports_serve_defaults() -> None:
    args = parse_args()

    assert args.host == "127.0.0.1"
    assert args.port == 8000


@mock.patch.object(sys, "tracebacklimit", new=0)
@mock.patch.object(sys, "argv", new=["ssg", "build"])
def test_no_verbosity_leaves_tracebacks_suppressed() -> None:
    parse_args()

    assert sys.tracebacklimit == 0


@mock.patch.object(sys, "tracebacklimit", new=0)
@mock.patch.object(sys, "argv", new=["ssg", "build", "-v"])
def test_verbose_flag_restores_tracebacks() -> None:
    args = parse_args()

    assert args.verbosity == 1
    assert sys.tracebacklimit == 1000


@mock.patch.object(sys, "tracebacklimit", new=0)
@mock.patch.object(sys, "argv", new=["ssg", "build", "-vv"])
def test_repeated_verbose_flag_raises_verbosity() -> None:
    args = parse_args()

    assert args.verbosity == 2
    assert sys.tracebacklimit == 1000


@mock.patch.object(sys, "argv", new=["ssg", "serve"])
def test_serve_uses_defaults() -> None:
    args = parse_args()

    assert args.subcommand == "serve"
    assert args.host == "127.0.0.1"
    assert args.port == 8000


@mock.patch.object(
    sys,
    "argv",
    new=["ssg", "serve", "--host", "0.0.0.0", "--port", "52467"],  # noqa: S104
)
def test_serve_accepts_host_and_port() -> None:
    args = parse_args()

    assert args.host == "0.0.0.0"  # noqa: S104
    assert args.port == 52467


@mock.patch.object(sys, "argv", new=["ssg"])
def test_subcommand_is_required() -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_args()

    assert exc_info.value.code == 2


@mock.patch.object(sys, "argv", new=["ssg", "--version"])
def test_version_flag_prints_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_args()

    assert exc_info.value.code == 0
    assert capsys.readouterr().out == f"ssg {__version__}\n"
