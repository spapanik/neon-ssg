from __future__ import annotations

from neon_ssg.commands.serve import ServeCommand


def test_stores_host_and_port() -> None:
    command = ServeCommand(verbosity=2, host="localhost", port=52467)

    assert command.verbosity == 2
    assert command.host == "localhost"
    assert command.port == 52467


def test_run_is_a_noop() -> None:
    command = ServeCommand(verbosity=0, host="localhost", port=52467)

    command.run()

    assert command.port == 52467
