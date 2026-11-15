from __future__ import annotations

from contextlib import chdir
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from neon_ssg.__main__ import main
from neon_ssg.commands.build import BuildCommand
from neon_ssg.lib.exceptions import BuildFailedError

if TYPE_CHECKING:
    from pathlib import Path


def test_build_renders_navigation_and_rewrites_links(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "README.md").write_text("# Home\n\n[Guide](guide.md)\n", encoding="utf-8")
    (docs / "guide.md").write_text("# Guide\n", encoding="utf-8")
    (tmp_path / "neon-ssg.yaml").write_text(
        "site:\n  name: Example\ncontent:\n  nav:\n"
        "    - Home: README.md\n    - Guides:\n        - Guide: guide.md\n",
        encoding="utf-8",
    )
    with chdir(tmp_path):
        BuildCommand(verbosity=0).run()
    home = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    guide = (tmp_path / "site" / "guide" / "index.html").read_text(encoding="utf-8")
    assert '<a href="guide/index.html">Guide</a>' in home
    assert '<a href="../index.html">Home</a>' in guide
    assert '<h1 id="guide">Guide</h1>' in guide


def test_failed_build_preserves_previous_output(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    page = docs / "index.md"
    page.write_text("# Working\n", encoding="utf-8")
    with chdir(tmp_path):
        BuildCommand(verbosity=0).run()
        output = tmp_path / "site" / "index.html"
        previous = output.read_text(encoding="utf-8")
        page.write_text("[Broken](missing.md)\n", encoding="utf-8")
        with pytest.raises(BuildFailedError, match="linked page not found"):
            BuildCommand(verbosity=0).run()
        assert output.read_text(encoding="utf-8") == previous


def test_include_source_is_relative_to_docs_directory(tmp_path: Path) -> None:
    (tmp_path / "manual").mkdir()
    (tmp_path / "LICENSE.md").write_text("# Licence\n", encoding="utf-8")
    (tmp_path / "neon-ssg.yaml").write_text(
        "content:\n  docs_root: manual\n  include:\n"
        "    - src: ../LICENSE.md\n      as: LICENSE.md\n"
        "  nav:\n    - Licence: LICENSE.md\n",
        encoding="utf-8",
    )
    with chdir(tmp_path):
        BuildCommand(verbosity=0).run()
    assert '<h1 id="licence">Licence</h1>' in (
        tmp_path / "site" / "LICENSE" / "index.html"
    ).read_text(encoding="utf-8")


def test_unmarked_directory_is_not_removed(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    output = tmp_path / "site"
    output.mkdir()
    (output / "important.txt").write_text("keep", encoding="utf-8")
    with chdir(tmp_path), pytest.raises(BuildFailedError, match="unmarked"):
        BuildCommand(verbosity=0).run()
    assert (output / "important.txt").read_text(encoding="utf-8") == "keep"


def test_configuration_error_and_output_override(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    config = tmp_path / "neon-ssg.yaml"
    config.write_text("site:\n  name: ''\n", encoding="utf-8")
    with chdir(tmp_path), pytest.raises(BuildFailedError):
        BuildCommand(0).run()
    config.write_text("{}", encoding="utf-8")
    with chdir(tmp_path):
        BuildCommand(0, site_root=tmp_path / "custom").run()
    assert (tmp_path / "custom" / ".neon-ssg").exists()


def test_main_reports_build_failure(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch("sys.argv", ["ssg", "build"]),
        patch("neon_ssg.__main__.BuildCommand", side_effect=BuildFailedError("bad")),
        pytest.raises(SystemExit, match="1"),
    ):
        main()
    assert capsys.readouterr().err == "bad\n"
