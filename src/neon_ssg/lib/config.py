from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path, PurePosixPath

DEFAULT_MARKDOWN_EXTENSIONS: Final[tuple[str, ...]] = (
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

DEFAULT_THEME_FEATURES: Final[frozenset[str]] = frozenset(
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


@dataclass(frozen=True, slots=True)
class SiteConfig:
    name: str
    description: str | None
    url: str | None
    author: str | None
    copyright: str | None


@dataclass(frozen=True, slots=True)
class IncludeEntry:
    src: Path
    target: PurePosixPath


@dataclass(frozen=True, slots=True)
class NavEntry:
    title: str | None
    target: PurePosixPath | None
    children: tuple[NavEntry, ...]


@dataclass(frozen=True, slots=True)
class ContentConfig:
    docs_root: Path
    site_root: Path
    include: tuple[IncludeEntry, ...]
    nav: tuple[NavEntry, ...] | None
    exclude: tuple[str, ...]
    not_found: PurePosixPath


@dataclass(frozen=True, slots=True)
class RepoConfig:
    url: str
    name: str
    provider: str | None
    branch: str
    edit_path: PurePosixPath | None


@dataclass(frozen=True, slots=True)
class ThemeConfig:
    name: str
    overrides: Path | None
    features: frozenset[str]
    palette: Mapping[str, str]
    icons: Mapping[str, str]
    logo: Path | None
    favicon: Path | None


@dataclass(frozen=True, slots=True)
class MarkdownConfig:
    extensions: tuple[str, ...]
    extension_config: Mapping[str, Mapping[str, object]]


@dataclass(frozen=True, slots=True)
class LocaleConfig:
    code: str
    name: str
    flag: str | None
    docs_dir: Path
    nav: Path | None


@dataclass(frozen=True, slots=True)
class I18nConfig:
    default: str
    fallback: bool
    locales: tuple[LocaleConfig, ...]


@dataclass(frozen=True, slots=True)
class VersionsConfig:
    provider: str
    branch: str
    default: str | None


@dataclass(frozen=True, slots=True)
class AssetsConfig:
    offline: bool
    vendor_dir: PurePosixPath


@dataclass(frozen=True, slots=True)
class Config:
    site: SiteConfig
    content: ContentConfig
    repo: RepoConfig | None
    theme: ThemeConfig
    markdown: MarkdownConfig
    i18n: I18nConfig
    versions: VersionsConfig
    assets: AssetsConfig
    plugins: tuple[str, ...]
    """Enabled plugin names, in load order.

    Names only: `plugins` is a mapping keyed by name (§4.2, rule 4), so a
    plugin's options are addressable at `("plugins", <name>)` and it resolves
    them itself through the parser (§7.3). Copying them here would be a second
    copy that could disagree with the one every layer feeds.
    """

    config_stem: Path
    resolution_root: Path
