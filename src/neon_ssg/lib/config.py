from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Final, TypeVar, cast
from urllib.parse import urlsplit

from dj_settings import UNDEFINED, ConfigParser, Sentinel
from dj_settings.lib.exceptions import SettingNotFoundError

from neon_ssg.lib.coercers import as_bool, as_str
from neon_ssg.lib.diagnostics import DiagnosticCode, DiagnosticCollector, diagnostic
from neon_ssg.lib.loader import ENV_NAMESPACE, ConfigSource
from neon_ssg.lib.validators import absolute_url, non_empty, one_of, within_root

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")

_REPO_SCALAR_PATHS: Final[frozenset[str]] = frozenset(
    {"repo.url", "repo.name", "repo.provider", "repo.branch", "repo.edit_path"}
)

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


class _ScalarResolver:
    __slots__ = ("cli_values", "collector", "failed", "parser")

    def __init__(
        self,
        parser: ConfigParser,
        collector: DiagnosticCollector,
        cli_values: Mapping[str, object],
    ) -> None:
        self.parser = parser
        self.collector = collector
        self.cli_values = cli_values
        self.failed: set[str] = set()

    def _cli_value(self, path: str) -> object:
        return self.cli_values.get(path, UNDEFINED)

    def _record(self, path: str, exc: Exception) -> None:
        self.failed.add(path)
        if isinstance(exc, SettingNotFoundError):
            message = f"'{path}' is required"
            hint = "\n".join(exc.__notes__)
        else:
            message = f"'{path}' {exc}"
            hint = None

        self.collector.add(
            diagnostic(DiagnosticCode.INVALID_CONFIG_VALUE, message, hint=hint)
        )

    def setting(
        self,
        path: str,
        *,
        rtype: Callable[[object], T],
        default: T,
        validator: Callable[[object], None] | None = None,
    ) -> T:
        sections, name = _setting_path(path)
        cli_value = cast("T | Sentinel", self._cli_value(path))
        try:
            return self.parser.get_setting(
                name,
                cli_value=cli_value,
                sections=sections,
                env_namespace=ENV_NAMESPACE,
                rtype=rtype,
                default=default,
                validator=validator,
            )
        except (SettingNotFoundError, TypeError, ValueError) as exc:
            self._record(path, exc)
            return default

    def optional(
        self,
        path: str,
        *,
        rtype: Callable[[object], T],
        default: T | None = None,
        validator: Callable[[object], None] | None = None,
    ) -> T | None:
        sections, name = _setting_path(path)
        cli_value = cast("T | Sentinel", self._cli_value(path))
        try:
            # dj_settings deliberately returns defaults without coercing them.
            # Casting here expresses its supported nullable-default behaviour.
            return self.parser.get_setting(
                name,
                cli_value=cli_value,
                sections=sections,
                env_namespace=ENV_NAMESPACE,
                rtype=rtype,
                default=cast("T", default),
                validator=validator,
            )
        except (SettingNotFoundError, TypeError, ValueError) as exc:
            self._record(path, exc)
            return default

    def required(
        self,
        path: str,
        *,
        rtype: Callable[[object], T],
        validator: Callable[[object], None] | None = None,
    ) -> T | None:
        sections, name = _setting_path(path)
        cli_value = cast("T | Sentinel", self._cli_value(path))
        try:
            return self.parser.get_setting(
                name,
                cli_value=cli_value,
                sections=sections,
                env_namespace=ENV_NAMESPACE,
                rtype=rtype,
                validator=validator,
            )
        except (SettingNotFoundError, TypeError, ValueError) as exc:
            self._record(path, exc)
            return None


def _setting_path(path: str) -> tuple[tuple[str, ...], str]:
    *sections, name = path.split(".")
    return tuple(sections), name


def _resolved_path(root: Path, value: str | None) -> Path | None:
    return None if value is None else (root / value).resolve()


def _repo_name(url: str | None) -> str:
    if url is None:
        return ""

    return urlsplit(url).path.rstrip("/").rsplit("/", maxsplit=1)[-1]


def _repo_provider(url: str | None) -> str | None:
    if url is None:
        return None

    providers = {
        "bitbucket.org": "bitbucket",
        "codeberg.org": "codeberg",
        "github.com": "github",
        "gitlab.com": "gitlab",
    }
    return providers.get(urlsplit(url).hostname or "")


def _repo_is_present(parser: ConfigParser, cli_values: Mapping[str, object]) -> bool:
    file_section = "repo" in parser.data
    environment = any(
        f"{ENV_NAMESPACE}__{path.replace('.', '__').upper()}" in os.environ
        for path in _REPO_SCALAR_PATHS
    )
    cli = any(
        path in _REPO_SCALAR_PATHS and not isinstance(value, Sentinel)
        for path, value in cli_values.items()
    )
    return file_section or environment or cli


def _locale_codes(parser: ConfigParser) -> tuple[str, ...]:
    i18n = parser.data.get("i18n")
    if not isinstance(i18n, Mapping):
        return ("en",)

    locales = i18n.get("locales")
    if not isinstance(locales, Mapping):
        return ("en",)

    codes = tuple(code for code in locales if isinstance(code, str))
    return codes or ("en",)


def resolve_config(
    source: ConfigSource,
    collector: DiagnosticCollector,
    *,
    cli_values: Mapping[str, object] | None = None,
) -> Config:
    """Resolve every scalar setting and assemble the interim configuration tree."""
    supplied_cli_values = {} if cli_values is None else cli_values
    resolver = _ScalarResolver(source.parser, collector, supplied_cli_values)
    root = source.resolution_root

    site = SiteConfig(
        name=resolver.setting(
            "site.name", rtype=as_str, default=root.name, validator=non_empty
        ),
        description=resolver.optional("site.description", rtype=as_str),
        url=resolver.optional("site.url", rtype=as_str, validator=absolute_url),
        author=resolver.optional("site.author", rtype=as_str),
        copyright=resolver.optional("site.copyright", rtype=as_str),
    )

    docs_root = resolver.setting(
        "content.docs_root", rtype=as_str, default="docs", validator=non_empty
    )
    site_root = resolver.setting(
        "content.site_root", rtype=as_str, default="site", validator=non_empty
    )
    not_found = resolver.setting(
        "content.not_found",
        rtype=as_str,
        default="404.html",
        validator=within_root,
    )
    content = ContentConfig(
        docs_root=(root / docs_root).resolve(),
        site_root=(root / site_root).resolve(),
        include=(),
        nav=None,
        exclude=(),
        not_found=PurePosixPath(not_found),
    )

    repo_present = _repo_is_present(source.parser, supplied_cli_values)
    if repo_present:
        repo_url = resolver.required("repo.url", rtype=as_str, validator=absolute_url)
    else:
        repo_url = resolver.optional("repo.url", rtype=as_str, validator=absolute_url)
    repo_name = resolver.setting(
        "repo.name",
        rtype=as_str,
        default=_repo_name(repo_url),
        validator=non_empty,
    )
    repo_provider = resolver.optional(
        "repo.provider", rtype=as_str, default=_repo_provider(repo_url)
    )
    repo_branch = resolver.setting(
        "repo.branch", rtype=as_str, default="main", validator=non_empty
    )
    repo_edit_path = resolver.optional(
        "repo.edit_path", rtype=as_str, validator=within_root
    )
    repo = (
        RepoConfig(
            url=repo_url,
            name=repo_name,
            provider=repo_provider,
            branch=repo_branch,
            edit_path=(
                None if repo_edit_path is None else PurePosixPath(repo_edit_path)
            ),
        )
        if repo_present and repo_url is not None
        else None
    )

    theme = ThemeConfig(
        name=resolver.setting(
            "theme.name", rtype=as_str, default="neon", validator=non_empty
        ),
        overrides=_resolved_path(
            root, resolver.optional("theme.overrides", rtype=as_str)
        ),
        features=DEFAULT_THEME_FEATURES,
        palette={},
        icons={},
        logo=_resolved_path(root, resolver.optional("theme.logo", rtype=as_str)),
        favicon=_resolved_path(root, resolver.optional("theme.favicon", rtype=as_str)),
    )

    markdown = MarkdownConfig(
        extensions=DEFAULT_MARKDOWN_EXTENSIONS,
        extension_config={},
    )

    i18n_default = resolver.setting(
        "i18n.default", rtype=as_str, default="en", validator=non_empty
    )
    i18n_fallback = resolver.setting("i18n.fallback", rtype=as_bool, default=True)
    locale_codes = _locale_codes(source.parser)
    locales = tuple(
        LocaleConfig(
            code=code,
            name=code,
            flag=None,
            docs_dir=content.docs_root,
            nav=None,
        )
        for code in locale_codes
    )
    if i18n_default not in locale_codes and "i18n.default" not in resolver.failed:
        collector.add(
            diagnostic(
                DiagnosticCode.INVALID_CONFIG_VALUE,
                f"'i18n.default' must name a configured locale, got {i18n_default!r}",
            )
        )
    i18n = I18nConfig(
        default=i18n_default,
        fallback=i18n_fallback,
        locales=locales,
    )

    versions = VersionsConfig(
        provider=resolver.setting(
            "versions.provider",
            rtype=as_str,
            default="git",
            validator=one_of("git", "json"),
        ),
        branch=resolver.setting(
            "versions.branch", rtype=as_str, default="gh-pages", validator=non_empty
        ),
        default=resolver.optional(
            "versions.default", rtype=as_str, validator=non_empty
        ),
    )

    assets = AssetsConfig(
        offline=resolver.setting("assets.offline", rtype=as_bool, default=False),
        vendor_dir=PurePosixPath(
            resolver.setting(
                "assets.vendor_dir",
                rtype=as_str,
                default="assets/vendor",
                validator=within_root,
            )
        ),
    )

    return Config(
        site=site,
        content=content,
        repo=repo,
        theme=theme,
        markdown=markdown,
        i18n=i18n,
        versions=versions,
        assets=assets,
        plugins=(),
        config_stem=source.stem,
        resolution_root=root,
    )
