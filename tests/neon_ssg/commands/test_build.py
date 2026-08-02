from __future__ import annotations

from pathlib import Path

from neon_ssg.commands.build import BuildCommand


def test_site_root_defaults_to_none() -> None:
    command = BuildCommand(verbosity=1)

    assert command.verbosity == 1
    assert command.site_root is None


def test_site_root_is_stored() -> None:
    site_root = Path("build/site")

    assert BuildCommand(verbosity=0, site_root=site_root).site_root == site_root


def test_run_is_a_noop() -> None:
    command = BuildCommand(verbosity=0)
    command.run()

    assert command.site_root is None
