from __future__ import annotations

from importlib.metadata import version

from neon_ssg.__version__ import __version__


def test_version_comes_from_installed_metadata() -> None:
    assert __version__ == version("neon-ssg")
