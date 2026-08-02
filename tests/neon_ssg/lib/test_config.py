from __future__ import annotations

from dataclasses import fields
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

import pytest

from neon_ssg.lib.config import (
    DEFAULT_MARKDOWN_EXTENSIONS,
    DEFAULT_THEME_FEATURES,
    AssetsConfig,
    Config,
    ContentConfig,
    I18nConfig,
    IncludeEntry,
    LocaleConfig,
    MarkdownConfig,
    NavEntry,
    RepoConfig,
    SiteConfig,
    ThemeConfig,
    VersionsConfig,
)

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

SCHEMA_KEYS: dict[type[DataclassInstance], set[str]] = {
    SiteConfig: {"name", "description", "url", "author", "copyright"},
    ContentConfig: {
        "docs_root",
        "site_root",
        "include",
        "nav",
        "exclude",
        "not_found",
    },
    IncludeEntry: {"src", "target"},
    NavEntry: {"title", "target", "children"},
    RepoConfig: {"url", "name", "provider", "branch", "edit_path"},
    ThemeConfig: {
        "name",
        "overrides",
        "features",
        "palette",
        "icons",
        "logo",
        "favicon",
    },
    MarkdownConfig: {"extensions", "extension_config"},
    LocaleConfig: {"code", "name", "flag", "docs_dir", "nav"},
    I18nConfig: {"default", "fallback", "locales"},
    VersionsConfig: {"provider", "branch", "default"},
    AssetsConfig: {"offline", "vendor_dir"},
    Config: {
        "site",
        "content",
        "repo",
        "theme",
        "markdown",
        "i18n",
        "versions",
        "assets",
        "plugins",
        "config_stem",
        "resolution_root",
    },
}

OFF_BY_DEFAULT = frozenset(
    {"nav.instant", "nav.instant_progress", "nav.sections_expand"}
)


def _site() -> SiteConfig:
    return SiteConfig(
        name="Neon Static Site Generator",
        description=None,
        url=None,
        author="Stephanos Kuma",
        copyright="© 2026 Stephanos Kuma",
    )


def _content(nav: tuple[NavEntry, ...] | None) -> ContentConfig:
    return ContentConfig(
        docs_root=Path("/project/docs"),
        site_root=Path("/project/site"),
        include=(
            IncludeEntry(
                src=Path("/project/LICENSE.md"), target=PurePosixPath("LICENSE.md")
            ),
        ),
        nav=nav,
        exclude=("**/_*.md",),
        not_found=PurePosixPath("404.html"),
    )


def _theme() -> ThemeConfig:
    return ThemeConfig(
        name="neon",
        overrides=None,
        features=DEFAULT_THEME_FEATURES,
        palette={},
        icons={"repo": "github"},
        logo=None,
        favicon=None,
    )


def _i18n() -> I18nConfig:
    locale = LocaleConfig(
        code="en", name="en", flag=None, docs_dir=Path("/project/docs"), nav=None
    )
    return I18nConfig(default="en", fallback=True, locales=(locale,))


def _config(
    *,
    nav: tuple[NavEntry, ...] | None = None,
    repo: RepoConfig | None = None,
) -> Config:
    return Config(
        site=_site(),
        content=_content(nav),
        repo=repo,
        theme=_theme(),
        markdown=MarkdownConfig(
            extensions=DEFAULT_MARKDOWN_EXTENSIONS, extension_config={}
        ),
        i18n=_i18n(),
        versions=VersionsConfig(provider="git", branch="gh-pages", default=None),
        assets=AssetsConfig(offline=False, vendor_dir=PurePosixPath("assets/vendor")),
        plugins=("search",),
        config_stem=Path("/project/neon-ssg.yaml"),
        resolution_root=Path("/project"),
    )


@pytest.mark.parametrize(
    ("model", "keys"),
    SCHEMA_KEYS.items(),
    ids=[model.__name__ for model in SCHEMA_KEYS],
)
def test_every_schema_key_has_a_home(
    model: type[DataclassInstance], keys: set[str]
) -> None:
    assert {field.name for field in fields(model)} == keys


@pytest.mark.parametrize("model", SCHEMA_KEYS, ids=lambda model: model.__name__)
def test_every_model_is_frozen_and_slotted(model: type[DataclassInstance]) -> None:
    assert model.__dataclass_params__.frozen  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
    assert hasattr(model, "__slots__")


def test_no_config_field_is_named_config_path() -> None:
    names = {field.name for field in fields(Config)}

    assert "config_path" not in names
    assert {"config_stem", "resolution_root"} <= names


def test_a_config_can_be_built() -> None:
    config = _config()

    assert config.site.name == "Neon Static Site Generator"
    assert config.content.include[0].target == PurePosixPath("LICENSE.md")
    assert config.i18n.locales[0].code == "en"
    assert config.plugins == ("search",)


def test_a_config_is_frozen() -> None:
    config = _config()

    with pytest.raises(AttributeError):
        config.repo = None  # type: ignore[misc]  # ty: ignore[invalid-assignment]


def test_an_absent_nav_is_not_an_empty_nav() -> None:
    derived = _config(nav=None)
    empty = _config(nav=())

    assert derived.content.nav is None
    assert empty.content.nav == ()
    assert derived.content.nav != empty.content.nav


def test_a_nav_entry_nests() -> None:
    child = NavEntry(title="License", target=PurePosixPath("LICENSE.md"), children=())
    section = NavEntry(title="About", target=None, children=(child,))
    bare = NavEntry(title=None, target=PurePosixPath("README.md"), children=())

    assert section.children == (child,)
    assert section.target is None
    assert bare.title is None


def test_a_site_without_a_repository_is_representable() -> None:
    assert _config().repo is None


def test_a_repository_carries_what_edit_links_need() -> None:
    repo = RepoConfig(
        url="https://github.com/spapanik/neon-ssg/",
        name="neon-ssg",
        provider="github",
        branch="main",
        edit_path=PurePosixPath("docs"),
    )

    assert _config(repo=repo).repo == repo


def test_the_default_extension_set_matches_the_spec() -> None:
    assert DEFAULT_MARKDOWN_EXTENSIONS == (
        "admonition",
        "pymdownx.details",
        "pymdownx.superfences",
        "pymdownx.highlight",
        "pymdownx.inlinehilite",
        "pymdownx.tabbed",
        "pymdownx.tasklist",
        "pymdownx.snippets",
        "pymdownx.smartsymbols",
        "attr_list",
        "def_list",
        "md_in_html",
        "footnotes",
        "tables",
        "abbr",
        "toc",
        "meta",
    )


def test_the_default_feature_set_matches_the_spec() -> None:
    assert (
        frozenset(
            {
                "code.copy",
                "code.annotate",
                "nav.breadcrumbs",
                "nav.index_pages",
                "nav.back_to_top",
                "nav.tracking",
                "toc.follow",
                "search",
                "search.suggest",
                "search.share",
                "content.tooltips",
            }
        )
        == DEFAULT_THEME_FEATURES
    )


def test_the_features_that_default_off_are_absent() -> None:
    assert not (DEFAULT_THEME_FEATURES & OFF_BY_DEFAULT)
