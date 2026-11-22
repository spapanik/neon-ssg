from __future__ import annotations

from contextlib import chdir
from dataclasses import replace
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING
from unittest.mock import patch
from xml.etree.ElementTree import Element, SubElement

import pytest

from neon_ssg.lib.build import _Links, _navigation, _relative_url, _safe_path, build
from neon_ssg.lib.config import Config, resolve_config
from neon_ssg.lib.diagnostics import DiagnosticCollector
from neon_ssg.lib.exceptions import BuildFailedError
from neon_ssg.lib.loader import discover

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def site(tmp_path: Path) -> Iterator[Config]:
    (tmp_path / "docs").mkdir()
    with chdir(tmp_path):
        yield resolve_config(discover(), DiagnosticCollector())


@pytest.mark.parametrize("value", ["/x", "", "../x", "a\\b"])
def test_unsafe_paths(value: str) -> None:
    with pytest.raises(BuildFailedError, match="Invalid content path"):
        _safe_path(value)


@pytest.mark.parametrize("nav", [None, [42], [{1: "x"}], [{"x": 3}], ["missing.md"]])
def test_invalid_navigation(nav: object) -> None:
    with pytest.raises(BuildFailedError):
        _navigation(nav, set(), PurePosixPath("index.md"))


def test_links_ignore_non_markdown() -> None:
    root = Element("div")
    for href in (
        None,
        "https://example.com/a.md",
        "//example.com/a.md",
        "#top",
        "asset.css",
    ):
        a = SubElement(root, "a")
        if href is not None:
            a.set("href", href)
    _Links(PurePosixPath("index.md"), set()).run(root)


@pytest.mark.parametrize(
    ("origin", "target", "expected"),
    [
        ("index.html", "index.html", "./"),
        ("index.html", "installation/index.html", "installation/"),
        ("installation/index.html", "index.html", "../"),
        ("a/b/index.html", "a/c/index.html", "../c/"),
        ("index.html", "a b/#guide/index.html", "a%20b/%23guide/"),
    ],
)
def test_relative_page_urls(origin: str, target: str, expected: str) -> None:
    assert _relative_url(PurePosixPath(origin), PurePosixPath(target)) == expected


@pytest.mark.parametrize(
    "content",
    [
        [],
        {"include": {}},
        {"include": [3]},
        {"include": [{}]},
        {"include": [{"src": "missing", "as": "x"}]},
    ],
)
def test_invalid_content(site: Config, content: object) -> None:
    with pytest.raises(BuildFailedError):
        build(site, {"content": content})


def test_missing_and_overlapping_directories(site: Config, tmp_path: Path) -> None:
    with pytest.raises(BuildFailedError, match="not found"):
        build(
            replace(
                site, content=replace(site.content, docs_root=tmp_path / "missing")
            ),
            {},
        )
    with pytest.raises(BuildFailedError, match="overlap"):
        build(
            replace(
                site, content=replace(site.content, site_root=site.content.docs_root)
            ),
            {},
        )


def test_duplicate_and_missing_include(site: Config, tmp_path: Path) -> None:
    (tmp_path / "docs" / "x.md").write_text("# X", encoding="utf-8")
    with pytest.raises(BuildFailedError, match="already exists"):
        build(site, {"content": {"include": [{"src": "x.md", "as": "x.md"}]}})
    (tmp_path / "docs" / "index.md").write_text("# X", encoding="utf-8")
    (tmp_path / "docs" / "README.md").write_text("# X", encoding="utf-8")
    with pytest.raises(BuildFailedError, match="same output"):
        build(site, {})


def test_assets_and_replacement(site: Config, tmp_path: Path) -> None:
    (tmp_path / "docs" / "asset.txt").write_text("asset", encoding="utf-8")
    build(site, {})
    build(site, {})
    assert (tmp_path / "site" / "asset.txt").read_text() == "asset"


def test_restore_after_publish_failure(site: Config, tmp_path: Path) -> None:
    build(site, {})
    original = Path.rename

    def rename(path: Path, target: Path) -> Path:
        if path.name == "site" and path.parent.name.startswith(".neon-build-"):
            msg = "publish failed"
            raise OSError(msg)
        return original(path, target)

    with patch.object(Path, "rename", rename), pytest.raises(OSError, match="publish"):
        build(site, {})
    assert (tmp_path / "site" / ".neon-ssg").exists()


def test_include_inside_output_is_rejected(site: Config, tmp_path: Path) -> None:
    output = tmp_path / "site"
    output.mkdir()
    (output / ".neon-ssg").write_text("marker", encoding="utf-8")
    (output / "source.md").write_text("# source", encoding="utf-8")
    with pytest.raises(BuildFailedError, match="contains a source"):
        build(
            site, {"content": {"include": [{"src": "../site/source.md", "as": "x.md"}]}}
        )


def test_first_publish_failure(site: Config) -> None:
    with (
        patch.object(Path, "rename", side_effect=OSError("publish failed")),
        pytest.raises(OSError, match="publish"),
    ):
        build(site, {})
