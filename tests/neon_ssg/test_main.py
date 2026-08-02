from __future__ import annotations

import sys
from unittest import mock

import neon_ssg.__main__
from neon_ssg.__main__ import main


@mock.patch.object(sys, "tracebacklimit", new=0)
@mock.patch.object(sys, "argv", new=["ssg", "build", "-v"])
@mock.patch.object(neon_ssg.__main__, "BuildCommand")
def test_build_is_dispatched(build_command: mock.MagicMock) -> None:
    main()

    assert build_command.call_count == 1
    assert build_command.call_args == mock.call(verbosity=1)
    assert build_command.return_value.run.call_count == 1
    assert build_command.return_value.run.call_args == mock.call()


@mock.patch.object(
    sys, "argv", new=["ssg", "serve", "--host", "localhost", "--port", "52467"]
)
@mock.patch.object(neon_ssg.__main__, "ServeCommand")
def test_serve_is_dispatched(serve_command: mock.MagicMock) -> None:
    main()

    assert serve_command.call_count == 1
    assert serve_command.call_args == mock.call(
        verbosity=0, host="localhost", port=52467
    )
    assert serve_command.return_value.run.call_count == 1
    assert serve_command.return_value.run.call_args == mock.call()
