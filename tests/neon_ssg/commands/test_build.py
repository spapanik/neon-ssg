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
    assert '<a href="guide/">Guide</a>' in home
    assert '<a href="../">Home</a>' in guide
    assert '<h1 id="guide">Guide</h1>' in guide


def test_nested_links_keep_queries_and_fragments(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    (docs / "guide").mkdir(parents=True)
    (docs / "README.md").write_text("# Home", encoding="utf-8")
    (docs / "guide" / "index.md").write_text(
        "# Guide\n\n[Home](../README.md?view=full#top)\n"
        "[Next](next%20steps.md#section)\n",
        encoding="utf-8",
    )
    (docs / "guide" / "next steps.md").write_text("# Next", encoding="utf-8")
    with chdir(tmp_path):
        BuildCommand(verbosity=0).run()
    guide = (tmp_path / "site" / "guide" / "index.html").read_text(encoding="utf-8")
    assert 'href="../?view=full#top"' in guide
    assert 'href="next%20steps/#section"' in guide
    assert (tmp_path / "site" / "guide" / "next steps" / "index.html").is_file()


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


def test_configurable_path_cleanup_and_asset_links(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    section = docs / "01-phonology"
    section.mkdir(parents=True)
    (docs / "00-index.md").write_text(
        "# Arcadia\n\n[Guide](01-phonology/00-index.md)", encoding="utf-8"
    )
    (section / "00-index.md").write_text(
        "# Guide\n\n![Diagram](diagram.png)\n\n[Home](../00-index.md)", encoding="utf-8"
    )
    (section / "diagram.png").write_bytes(b"image")
    (tmp_path / "neon-ssg.yaml").write_text(
        "content:\n  remove_prefix: '\\d\\d-'\n  nav:\n"
        "    - Home: 00-index.md\n    - Guide: 01-phonology/00-index.md\n",
        encoding="utf-8",
    )
    with chdir(tmp_path):
        BuildCommand(0).run()
    home = (tmp_path / "site/index.html").read_text(encoding="utf-8")
    guide = (tmp_path / "site/phonology/index.html").read_text(encoding="utf-8")
    assert 'href="phonology/"' in home
    assert 'href="../">Home</a>' in guide
    assert 'src="../01-phonology/diagram.png"' in guide
    assert (tmp_path / "site/01-phonology/diagram.png").is_file()


def test_suffix_cleanup_and_collisions(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index-00.md").write_text("# Home", encoding="utf-8")
    config = tmp_path / "neon-ssg.yaml"
    config.write_text("content:\n  remove_suffix: '-\\d\\d'\n", encoding="utf-8")
    with chdir(tmp_path):
        BuildCommand(0).run()
        assert (tmp_path / "site/index.html").exists()
        (docs / "index.md").write_text("# Duplicate", encoding="utf-8")
        BuildCommand(0).run()
        assert "Home" in (tmp_path / "site/index.html").read_text(encoding="utf-8")
        (docs / "guide-01.md").write_text("# One", encoding="utf-8")
        (docs / "guide-02.md").write_text("# Two", encoding="utf-8")
        with pytest.raises(BuildFailedError, match="same output"):
            BuildCommand(0).run()


def test_invalid_cleanup_pattern_is_configuration_error(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "neon-ssg.yaml").write_text(
        "content:\n  remove_prefix: '['\n", encoding="utf-8"
    )
    with chdir(tmp_path), pytest.raises(BuildFailedError):
        BuildCommand(0).run()


def test_section_index_links_and_explicit_labels(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    section = docs / "01-phonology"
    section.mkdir(parents=True)
    (docs / "index.md").write_text("# Home", encoding="utf-8")
    (section / "00-index.md").write_text("# Introduction", encoding="utf-8")
    (section / "01-letters.md").write_text("# Letters", encoding="utf-8")
    config = tmp_path / "neon-ssg.yaml"
    config.write_text(
        "content:\n  remove_prefix: '\\d\\d-'\n  nav:\n"
        "    - Home: index.md\n    - Phonology:\n"
        "        - 01-phonology/00-index.md\n"
        "        - Letters: 01-phonology/01-letters.md\n",
        encoding="utf-8",
    )
    with chdir(tmp_path):
        BuildCommand(0).run()
        html = (tmp_path / "site/index.html").read_text(encoding="utf-8")
        assert '<a href="phonology/">Phonology</a>' in html
        assert ">00-index</a>" not in html
        assert '<a href="phonology/letters/">Letters</a>' in html
        config.write_text(
            config.read_text(encoding="utf-8").replace(
                "- 01-phonology/00-index.md", "- Overview: 01-phonology/00-index.md"
            ),
            encoding="utf-8",
        )
        BuildCommand(0).run()
    html = (tmp_path / "site/index.html").read_text(encoding="utf-8")
    assert "<li>Phonology<ul>" in html
    assert '<a href="phonology/">Overview</a>' in html


def test_index_selection_and_alias_links(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    for name in ("02-index.md", "01-index.md", "00-README.md", "03-README.md"):
        (docs / name).write_text(f"# {name}", encoding="utf-8")
    (docs / "other.md").write_text("[Readme](00-README.md)", encoding="utf-8")
    (tmp_path / "neon-ssg.yaml").write_text(
        "content:\n  remove_prefix: '\\d\\d-'\n", encoding="utf-8"
    )
    with chdir(tmp_path):
        BuildCommand(0).run()
        assert "01-index.md" in (tmp_path / "site/index.html").read_text(
            encoding="utf-8"
        )
        assert 'href="../"' in (tmp_path / "site/other/index.html").read_text(
            encoding="utf-8"
        )
        (docs / "01-index.md").unlink()
        (docs / "02-index.md").unlink()
        BuildCommand(0).run()
        assert "00-README.md" in (tmp_path / "site/index.html").read_text(
            encoding="utf-8"
        )
