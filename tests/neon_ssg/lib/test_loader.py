from __future__ import annotations

import os
from contextlib import chdir
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import dj_settings.lib.utils
import pytest

from neon_ssg.lib.exceptions import UnreadableConfigError
from neon_ssg.lib.loader import CONFIG_FILENAME, DIR_NAMESPACE, discover

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass(frozen=True, slots=True)
class Tiers:
    etc: Path
    xdg: Path
    project: Path

    def config(self, tier: Path, name: str = CONFIG_FILENAME) -> Path:
        return tier / name if tier == self.project else tier / DIR_NAMESPACE / name


@pytest.fixture
def tiers(tmp_path: Path) -> Iterator[Tiers]:
    etc = tmp_path / "etc"
    xdg = tmp_path / "xdg"
    project = tmp_path / "project"
    project.mkdir()
    with (
        mock.patch.object(dj_settings.lib.utils, "ETC", new=etc),
        mock.patch.object(dj_settings.lib.utils, "HOME_CONF", new=xdg),
        chdir(project),
    ):
        yield Tiers(etc=etc, xdg=xdg, project=project)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_project_config_is_discovered_without_flags(tiers: Tiers) -> None:
    _write(tiers.config(tiers.project), "site:\n  name: Discovered\n")

    source = discover()

    assert source.parser.data == {"site": {"name": "Discovered"}}
    assert source.stem == Path.cwd() / CONFIG_FILENAME


def test_no_config_anywhere_is_not_an_error(tiers: Tiers) -> None:
    assert discover().parser.data == {}
    assert tiers.project.exists()


def test_the_project_tier_beats_the_user_tier_which_beats_the_system_tier(
    tiers: Tiers,
) -> None:
    _write(
        tiers.config(tiers.etc),
        "site:\n  name: from-etc\n  author: from-etc\n  copyright: from-etc\n",
    )
    _write(tiers.config(tiers.xdg), "site:\n  name: from-xdg\n  author: from-xdg\n")
    _write(tiers.config(tiers.project), "site:\n  name: from-project\n")

    site = discover().parser.data["site"]

    assert site["name"] == "from-project"
    assert site["author"] == "from-xdg"
    assert site["copyright"] == "from-etc"


def test_an_override_directory_is_merged_alphabetically(tiers: Tiers) -> None:
    config = _write(tiers.config(tiers.project), "site:\n  name: base\n")
    overrides = config.with_suffix(f"{config.suffix}.d")
    _write(overrides / "01-first.yaml", "site:\n  name: first\n  url: kept\n")
    _write(overrides / "02-second.yaml", "site:\n  name: second\n")

    site = discover().parser.data["site"]

    assert site["name"] == "second"
    assert site["url"] == "kept"


def test_only_the_namespaced_tier_is_read(tiers: Tiers) -> None:
    _write(tiers.etc / CONFIG_FILENAME, "site:\n  name: flat\n")
    _write(tiers.config(tiers.etc), "site:\n  name: namespaced\n")

    assert discover().parser.data == {"site": {"name": "namespaced"}}


def test_an_explicit_config_is_the_highest_file_tier(tiers: Tiers) -> None:
    named = _write(tiers.project / "custom.yaml", "site:\n  name: from-flag\n")
    _write(
        tiers.config(tiers.xdg, "custom.yaml"),
        "site:\n  name: from-xdg\n  author: from-xdg\n",
    )

    site = discover(named).parser.data["site"]

    assert site["name"] == "from-flag"
    assert site["author"] == "from-xdg", "-f cannot suppress the operator's tiers"


def test_an_explicit_config_that_is_missing_is_an_error(tiers: Tiers) -> None:
    missing = tiers.project / "nope.yaml"

    with pytest.raises(UnreadableConfigError) as exc_info:
        discover(missing)

    assert exc_info.value.exit_code == 2
    assert str(missing) in str(exc_info.value)


def test_a_directory_is_not_a_config_file(tiers: Tiers) -> None:
    with pytest.raises(UnreadableConfigError, match="not found"):
        discover(tiers.project)


@mock.patch.object(os, "access", return_value=False)
def test_an_unreadable_explicit_config_is_an_error(
    access: mock.MagicMock, tiers: Tiers
) -> None:
    named = _write(tiers.project / "custom.yaml", "site:\n  name: unreadable\n")

    with pytest.raises(UnreadableConfigError, match="not readable"):
        discover(named)

    assert access.call_count == 1


def test_a_malformed_config_is_an_error(tiers: Tiers) -> None:
    _write(tiers.config(tiers.project), "site: [1, 2\n")

    with pytest.raises(UnreadableConfigError) as exc_info:
        discover()

    assert exc_info.value.exit_code == 2
    assert CONFIG_FILENAME in str(exc_info.value)


def test_a_config_that_is_not_a_mapping_is_an_error(tiers: Tiers) -> None:
    _write(tiers.config(tiers.project), "- one\n- two\n")

    with pytest.raises(UnreadableConfigError, match="cannot read the configuration"):
        discover()


def test_a_format_we_cannot_infer_is_an_error(tiers: Tiers) -> None:
    named = _write(tiers.project / "config.txt", "site:\n  name: mystery\n")

    with pytest.raises(UnreadableConfigError, match="cannot read the configuration"):
        discover(named)


def test_the_resolution_root_is_the_working_directory_without_a_flag(
    tiers: Tiers,
) -> None:
    _write(tiers.config(tiers.project), "site:\n  name: Discovered\n")

    assert discover().resolution_root == Path.cwd()


def test_the_resolution_root_is_the_named_files_parent_with_a_flag(
    tiers: Tiers,
) -> None:
    named = _write(tiers.project / "docs" / CONFIG_FILENAME, "site:\n  name: Deep\n")

    source = discover(named)

    assert source.resolution_root == named.parent.resolve()
    assert source.resolution_root != Path.cwd()
