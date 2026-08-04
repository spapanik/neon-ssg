from __future__ import annotations

import os
from contextlib import chdir
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING
from unittest import mock

import dj_settings.lib.utils
import pytest

from neon_ssg.lib.config import (
    DEFAULT_MARKDOWN_EXTENSIONS,
    DEFAULT_THEME_FEATURES,
    Config,
    resolve_config,
)
from neon_ssg.lib.diagnostics import DiagnosticCode, DiagnosticCollector
from neon_ssg.lib.loader import CONFIG_FILENAME, DIR_NAMESPACE, discover

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass(frozen=True, slots=True)
class Tiers:
    etc: Path
    xdg: Path
    project: Path

    def config(self, tier: Path) -> Path:
        return (
            tier / CONFIG_FILENAME
            if tier == self.project
            else tier / DIR_NAMESPACE / CONFIG_FILENAME
        )


@pytest.fixture
def tiers(tmp_path: Path) -> Iterator[Tiers]:
    etc = tmp_path / "etc"
    xdg = tmp_path / "xdg"
    project = tmp_path / "project"
    project.mkdir()
    clean_environment = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("NEON_SSG__")
    }
    with (
        mock.patch.object(dj_settings.lib.utils, "ETC", new=etc),
        mock.patch.object(dj_settings.lib.utils, "HOME_CONF", new=xdg),
        mock.patch.dict(os.environ, clean_environment, clear=True),
        chdir(project),
    ):
        yield Tiers(etc=etc, xdg=xdg, project=project)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _resolve(
    *, cli_values: dict[str, object] | None = None
) -> tuple[Config, DiagnosticCollector]:
    collector = DiagnosticCollector()
    config = resolve_config(discover(), collector, cli_values=cli_values)
    return config, collector


def test_every_scalar_is_resolved_into_the_model(tiers: Tiers) -> None:
    _write(
        tiers.config(tiers.project),
        """
site:
  name: Project
  description: Description
  url: https://example.com/docs/
  author: Author
  copyright: Copyright
content:
  docs_root: ../manual
  site_root: ../published
  not_found: missing.html
repo:
  url: https://gitlab.com/group/project/
  name: Repository
  provider: custom
  branch: trunk
  edit_path: source/
theme:
  name: bright
  overrides: ../overrides
  logo: ../brand/logo.svg
  favicon: ../brand/favicon.svg
i18n:
  default: en
  fallback: false
  locales:
    en: {}
versions:
  provider: json
  branch: pages
  default: stable
assets:
  offline: true
  vendor_dir: static/vendor
""",
    )

    config, collector = _resolve()

    assert config.site.name == "Project"
    assert config.site.description == "Description"
    assert config.site.url == "https://example.com/docs/"
    assert config.site.author == "Author"
    assert config.site.copyright == "Copyright"
    assert config.content.docs_root == (tiers.project / "../manual").resolve()
    assert config.content.site_root == (tiers.project / "../published").resolve()
    assert config.content.not_found == PurePosixPath("missing.html")
    assert config.repo is not None
    assert config.repo.url == "https://gitlab.com/group/project/"
    assert config.repo.name == "Repository"
    assert config.repo.provider == "custom"
    assert config.repo.branch == "trunk"
    assert config.repo.edit_path == PurePosixPath("source")
    assert config.theme.name == "bright"
    assert config.theme.overrides == (tiers.project / "../overrides").resolve()
    assert config.theme.logo == (tiers.project / "../brand/logo.svg").resolve()
    assert config.theme.favicon == (tiers.project / "../brand/favicon.svg").resolve()
    assert config.i18n.default == "en"
    assert config.i18n.fallback is False
    assert config.versions.provider == "json"
    assert config.versions.branch == "pages"
    assert config.versions.default == "stable"
    assert config.assets.offline is True
    assert config.assets.vendor_dir == PurePosixPath("static/vendor")
    assert collector.diagnostics == ()


def test_file_tiers_and_the_default_layer_are_respected(tiers: Tiers) -> None:
    _write(tiers.config(tiers.etc), "site:\n  author: System\n")
    _write(tiers.config(tiers.xdg), "site:\n  description: User\n")
    _write(tiers.config(tiers.project), "site:\n  copyright: Project\n")

    config, collector = _resolve()

    assert config.site.author == "System"
    assert config.site.description == "User"
    assert config.site.copyright == "Project"
    assert config.site.name == tiers.project.name
    assert config.theme.name == "neon"
    assert config.markdown.extensions == DEFAULT_MARKDOWN_EXTENSIONS
    assert config.theme.features == DEFAULT_THEME_FEATURES
    assert config.assets.offline is False
    assert collector.diagnostics == ()


def test_environment_beats_the_file_and_cli_beats_the_environment(
    tiers: Tiers,
) -> None:
    _write(tiers.config(tiers.project), "site:\n  name: File\n")
    with mock.patch.dict(os.environ, {"NEON_SSG__SITE__NAME": "Environment"}):
        environment, _ = _resolve()
        cli, _ = _resolve(cli_values={"site.name": "CLI"})

    assert environment.site.name == "Environment"
    assert cli.site.name == "CLI"


@pytest.mark.parametrize(("value", "expected"), [("true", True), ("FALSE", False)])
@pytest.mark.usefixtures("tiers")
def test_boolean_environment_values_are_coerced(value: str, expected: bool) -> None:
    with mock.patch.dict(os.environ, {"NEON_SSG__ASSETS__OFFLINE": value}):
        config, collector = _resolve()

    assert config.assets.offline is expected
    assert collector.diagnostics == ()


@pytest.mark.usefixtures("tiers")
def test_an_invalid_boolean_is_reported_and_uses_its_default() -> None:
    with mock.patch.dict(os.environ, {"NEON_SSG__ASSETS__OFFLINE": "yes"}):
        config, collector = _resolve()

    assert config.assets.offline is False
    assert len(collector.errors) == 1
    assert collector.errors[0].code is DiagnosticCode.INVALID_CONFIG_VALUE
    assert collector.errors[0].message == (
        "'assets.offline' expects a boolean, got 'yes'"
    )


def test_explicit_null_is_an_error_while_absence_uses_none(tiers: Tiers) -> None:
    _write(tiers.config(tiers.project), "site:\n  description:\n")

    explicit, explicit_collector = _resolve()
    tiers.config(tiers.project).unlink()
    absent, absent_collector = _resolve()

    assert explicit.site.description is None
    assert explicit_collector.errors[0].message == (
        "'site.description' expects a string, got null"
    )
    assert absent.site.description is None
    assert absent_collector.diagnostics == ()


def test_resolution_collects_more_than_one_bad_key(tiers: Tiers) -> None:
    _write(
        tiers.config(tiers.project),
        "site:\n  url: relative.example\nassets:\n  offline: yes\n",
    )

    _, collector = _resolve()

    assert len(collector.errors) == 2
    assert {entry.message.split("'", maxsplit=2)[1] for entry in collector.errors} == {
        "site.url",
        "assets.offline",
    }


def test_a_missing_required_repo_url_reports_the_consulted_layers(
    tiers: Tiers,
) -> None:
    _write(tiers.config(tiers.project), "repo:\n  name: Project\n")

    config, collector = _resolve()

    assert config.repo is None
    assert len(collector.errors) == 1
    assert collector.errors[0].message == "'repo.url' is required"
    assert collector.errors[0].hint is not None
    assert "NEON_SSG__REPO__URL" in collector.errors[0].hint
    assert "repo.url" in collector.errors[0].hint


def test_repo_defaults_are_derived_from_the_url(tiers: Tiers) -> None:
    _write(
        tiers.config(tiers.project),
        "repo:\n  url: https://github.com/example/project/\n",
    )

    config, collector = _resolve()

    assert config.repo is not None
    assert config.repo.name == "project"
    assert config.repo.provider == "github"
    assert collector.diagnostics == ()


@pytest.mark.usefixtures("tiers")
def test_an_environment_repo_url_enables_the_repo() -> None:
    with mock.patch.dict(
        os.environ,
        {"NEON_SSG__REPO__URL": "https://github.com/example/environment/"},
    ):
        config, collector = _resolve()

    assert config.repo is not None
    assert config.repo.name == "environment"
    assert config.repo.provider == "github"
    assert collector.diagnostics == ()


@pytest.mark.usefixtures("tiers")
def test_an_unknown_environment_name_does_not_enable_the_repo() -> None:
    with mock.patch.dict(os.environ, {"NEON_SSG__REPO__UNKNOWN": "ignored"}):
        config, collector = _resolve()

    assert config.repo is None
    assert collector.diagnostics == ()


def test_an_unknown_default_locale_is_reported(tiers: Tiers) -> None:
    _write(
        tiers.config(tiers.project),
        "i18n:\n  default: el\n  locales:\n    en: {}\n",
    )

    config, collector = _resolve()

    assert config.i18n.default == "el"
    assert len(collector.errors) == 1
    assert collector.errors[0].message == (
        "'i18n.default' must name a configured locale, got 'el'"
    )


def test_absent_i18n_becomes_one_locale_using_the_docs_root(tiers: Tiers) -> None:
    _write(tiers.config(tiers.project), "content:\n  docs_root: handbook\n")

    config, collector = _resolve()

    assert config.i18n.default == "en"
    assert config.i18n.fallback is True
    assert len(config.i18n.locales) == 1
    assert config.i18n.locales[0].code == "en"
    assert config.i18n.locales[0].docs_dir == config.content.docs_root
    assert collector.diagnostics == ()


def test_i18n_scalars_without_a_locale_map_still_use_one_locale(
    tiers: Tiers,
) -> None:
    _write(tiers.config(tiers.project), "i18n:\n  fallback: false\n")

    config, collector = _resolve()

    assert config.i18n.fallback is False
    assert tuple(locale.code for locale in config.i18n.locales) == ("en",)
    assert collector.diagnostics == ()


def test_a_user_tier_path_is_resolved_against_the_project(tiers: Tiers) -> None:
    _write(
        tiers.config(tiers.xdg),
        "content:\n  docs_root: shared-docs\ntheme:\n  logo: brand/logo.svg\n",
    )

    config, collector = _resolve()

    assert config.content.docs_root == (tiers.project / "shared-docs").resolve()
    assert config.theme.logo == (tiers.project / "brand/logo.svg").resolve()
    assert collector.diagnostics == ()
