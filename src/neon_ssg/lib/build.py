from __future__ import annotations

import posixpath
import re
import shutil
import tempfile
from html import escape
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import markdown
from jinja2 import Environment, select_autoescape
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
from markupsafe import Markup

from neon_ssg.lib.exceptions import BuildFailedError

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from neon_ssg.lib.config import Config

MARKER = ".neon-ssg"
TEMPLATE = """<!doctype html>
<html lang="{{ language }}">
<head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }}
· {{ site_name }}</title>
<style>body{font:16px/1.6 system-ui,sans-serif;margin:0;color:#202334}
header{background:#252044;color:white;padding:1rem 2rem;font-weight:bold}
.layout{display:flex;gap:2rem;max-width:80rem;margin:auto;padding:2rem}
nav{min-width:14rem}
nav ul{list-style:none;padding-left:1rem}
nav>ul{padding:0}
a{color:#6142a6}
main{min-width:0;max-width:55rem}
pre{overflow:auto;background:#f3f2f8;padding:1rem}
img{max-width:100%}
@media(max-width:700px){.layout{display:block}}</style></head>
<body><header>{{ site_name }}</header><div class="layout">
<nav aria-label="Site navigation">{{ navigation }}</nav>
<main>{{ content }}</main></div></body></html>
"""


def _clean_component(
    part: str, source: PurePosixPath, prefix: str | None, suffix: str | None
) -> str:
    if prefix is not None:
        match = re.match(prefix, part)
        if match:
            part = part[match.end() :]
    if suffix is not None:
        matches = (
            match for match in re.finditer(suffix, part) if match.end() == len(part)
        )
        match = next(matches, None)
        if match:
            part = part[: match.start()]
    if not part or part in {".", ".."} or "/" in part or "\\" in part:
        msg = f"Invalid output path component for {source}: {part!r}"
        raise BuildFailedError(msg)
    return part


def page_path(
    source: PurePosixPath, prefix: str | None = None, suffix: str | None = None
) -> PurePosixPath:
    parts = [
        _clean_component(part, source, prefix, suffix) for part in source.parts[:-1]
    ]
    name = _clean_component(source.stem, source, prefix, suffix)
    if name.lower() not in {"index", "readme"}:
        parts.append(name)
    return PurePosixPath(*parts, "index.html")


def _relative_url(origin: PurePosixPath, target: PurePosixPath) -> str:
    relative = posixpath.relpath(str(target.parent), str(origin.parent))
    return f"{quote(relative, safe='/')}/"


class _Links(Treeprocessor):
    def __init__(
        self,
        origin: PurePosixPath,
        pages: set[PurePosixPath],
        outputs: dict[PurePosixPath, PurePosixPath] | None = None,
    ) -> None:
        super().__init__()
        self.origin = origin
        self.pages = pages
        self.outputs = outputs or {page: page_path(page) for page in pages}

    def run(self, root: Element) -> None:
        for element in root.iter():
            attribute = (
                "src"
                if element.tag == "img"
                else "href"
                if element.tag == "a"
                else None
            )
            if attribute is None:
                continue
            href = element.get(attribute)
            if not href:
                continue
            parts = urlsplit(href)
            if (
                parts.scheme
                or parts.netloc
                or not parts.path
                or parts.path.startswith("/")
            ):
                continue
            path = PurePosixPath(
                posixpath.normpath(str(self.origin.parent / unquote(parts.path)))
            )
            if path not in self.outputs and parts.path.lower().endswith(".md"):
                msg = f"{self.origin}: linked page not found: {parts.path}"
                raise BuildFailedError(msg)
            if path not in self.outputs:
                continue
            target = self.outputs[path]
            if path in self.pages:
                url = _relative_url(self.outputs[self.origin], target)
            else:
                url = quote(
                    posixpath.relpath(
                        str(target), str(self.outputs[self.origin].parent)
                    ),
                    safe="/",
                )
            element.set(
                attribute,
                urlunsplit(
                    (
                        "",
                        "",
                        url,
                        parts.query,
                        parts.fragment,
                    )
                ),
            )


class _LinkExtension(Extension):
    def __init__(
        self,
        origin: PurePosixPath,
        pages: set[PurePosixPath],
        outputs: dict[PurePosixPath, PurePosixPath] | None = None,
    ) -> None:
        super().__init__()
        self.origin = origin
        self.pages = pages
        self.outputs = outputs or {page: page_path(page) for page in pages}

    def extendMarkdown(self, md: markdown.Markdown) -> None:  # noqa: N802
        md.treeprocessors.register(
            _Links(self.origin, self.pages, self.outputs), "neon_links", 5
        )


def _safe_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or ".." in path.parts or "\\" in value:
        msg = f"Invalid content path: {value!r}"
        raise BuildFailedError(msg)
    return path


def _navigation(
    entries: object,
    pages: set[PurePosixPath],
    origin: PurePosixPath,
    outputs: dict[PurePosixPath, PurePosixPath] | None = None,
    indexes: dict[PurePosixPath, PurePosixPath] | None = None,
) -> str:
    if not isinstance(entries, list):
        msg = "content.nav must be a list"
        raise BuildFailedError(msg)
    outputs = outputs or {page: page_path(page) for page in pages}
    result = []
    for item in entries:
        value: object
        if isinstance(item, str):
            title, value = PurePosixPath(item).stem, item
        elif isinstance(item, dict) and len(item) == 1:
            title, value = next(iter(item.items()))
            if not isinstance(title, str):
                msg = "Navigation titles must be strings"
                raise BuildFailedError(msg)
        else:
            msg = f"Invalid navigation entry: {item!r}"
            raise BuildFailedError(msg)
        if isinstance(value, list):
            # A bare directory-index entry becomes the group link. An explicit
            # label keeps its own entry and takes precedence over this behaviour.
            index_pages = set(indexes or {})
            explicit = {
                _safe_path(target)
                for child in value
                if isinstance(child, dict) and len(child) == 1
                for target in child.values()
                if isinstance(target, str)
            }
            candidates = [
                _safe_path(child)
                for child in value
                if isinstance(child, str) and _safe_path(child) in index_pages
            ]
            target = next(
                (
                    candidate
                    for candidate in candidates
                    if not any(
                        outputs.get(explicit_page) == outputs.get(candidate)
                        for explicit_page in explicit
                    )
                ),
                None,
            )
            children = value
            label = escape(title)
            if target is not None:
                url = escape(
                    _relative_url(outputs[origin], outputs[target]), quote=True
                )
                label = f'<a href="{url}">{label}</a>'
                children = [child for child in value if child != str(target)]
            nested = _navigation(children, pages, origin, outputs, indexes)
            result.append(f"<li>{label}{nested}</li>")
        elif isinstance(value, str):
            target = _safe_path(value)
            if target not in pages:
                msg = f"Navigation page not found: {value}"
                raise BuildFailedError(msg)
            url = escape(_relative_url(outputs[origin], outputs[target]), quote=True)
            result.append(f'<li><a href="{url}">{escape(title)}</a></li>')
        else:
            msg = f"Invalid navigation entry: {item!r}"
            raise BuildFailedError(msg)
    return "<ul>" + "".join(result) + "</ul>"


def build(config: Config, data: object) -> None:
    docs = config.content.docs_root.resolve()
    output = config.content.site_root.resolve()
    if not docs.is_dir():
        msg = f"Documentation directory not found: {docs}"
        raise BuildFailedError(msg)
    if output == docs or output in docs.parents or docs in output.parents:
        msg = "The output and documentation directories must not overlap"
        raise BuildFailedError(msg)
    if output.exists() and (
        not output.is_dir()
        or (any(output.iterdir()) and not (output / MARKER).is_file())
    ):
        msg = f"Refusing to replace unmarked output directory: {output}"
        raise BuildFailedError(msg)

    files = {
        PurePosixPath(p.relative_to(docs).as_posix()): p
        for p in sorted(docs.rglob("*"))
        if p.is_file()
        and not any(part.startswith(".") for part in p.relative_to(docs).parts)
    }
    content = data.get("content", {}) if isinstance(data, dict) else {}
    if not isinstance(content, dict):
        msg = "content must be a mapping"
        raise BuildFailedError(msg)
    includes = content.get("include", [])
    if not isinstance(includes, list):
        msg = "content.include must be a list"
        raise BuildFailedError(msg)
    for entry in includes:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("src"), str)
            or not isinstance(entry.get("as"), str)
        ):
            msg = "Each content.include entry needs 'src' and 'as' paths"
            raise BuildFailedError(msg)
        include_target = _safe_path(entry["as"])
        source = (docs / entry["src"]).resolve()
        if include_target in files:
            msg = f"Include target already exists: {include_target}"
            raise BuildFailedError(msg)
        if not source.is_file():
            msg = f"Included file not found: {source}"
            raise BuildFailedError(msg)
        files[include_target] = source
    if any(
        output == source.resolve() or output in source.resolve().parents
        for source in files.values()
    ):
        msg = "The output directory contains a source file"
        raise BuildFailedError(msg)
    pages = {path for path in files if path.suffix.lower() == ".md"}
    outputs = {
        path: page_path(
            path, config.content.remove_prefix, config.content.remove_suffix
        )
        if path in pages
        else path
        for path in files
    }
    # Only index candidates from the same source directory may share an output.
    indexes: dict[PurePosixPath, PurePosixPath] = {}
    candidates: dict[PurePosixPath, list[tuple[int, PurePosixPath]]] = {}
    for path in pages:
        name = _clean_component(
            path.stem, path, config.content.remove_prefix, config.content.remove_suffix
        ).lower()
        if name in {"index", "readme"}:
            candidates.setdefault(path.parent, []).append(
                (0 if name == "index" else 1, path)
            )
    skipped: set[PurePosixPath] = set()
    for group in candidates.values():
        winner = min(group)[1]
        for _, path in group:
            indexes[path] = winner
            if path != winner:
                skipped.add(path)
                outputs[path] = outputs[winner]
    published = [
        output_path for path, output_path in outputs.items() if path not in skipped
    ]
    if len(set(published)) != len(published) or PurePosixPath(MARKER) in published:
        msg = "Multiple inputs would produce the same output path"
        raise BuildFailedError(msg)
    nav = content.get("nav", [str(path) for path in sorted(pages - skipped)])
    template = Environment(autoescape=select_autoescape(default=True)).from_string(
        TEMPLATE
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".neon-build-", dir=output.parent) as tmp:
        staging = Path(tmp) / "site"
        staging.mkdir()
        for path, source in files.items():
            if path in skipped:
                continue
            target = staging / outputs[path]
            target.parent.mkdir(parents=True, exist_ok=True)
            if path not in pages:
                shutil.copyfile(source, target)
                continue
            text = source.read_text(encoding="utf-8")
            converter = markdown.Markdown(
                extensions=[
                    *config.markdown.extensions,
                    _LinkExtension(path, pages, outputs),
                ]
            )
            html = converter.convert(text)
            title = next(
                (
                    line.lstrip("# ").strip()
                    for line in text.splitlines()
                    if line.startswith("# ")
                ),
                path.stem,
            )
            rendered = template.render(
                title=title,
                site_name=config.site.name,
                language=config.i18n.default,
                navigation=Markup(_navigation(nav, pages, path, outputs, indexes)),  # noqa: S704
                content=Markup(html),  # noqa: S704
            )
            target.write_text(rendered, encoding="utf-8")
        (staging / MARKER).write_text("neon-ssg output\n", encoding="utf-8")
        previous = Path(tmp) / "previous"
        if output.exists():
            output.rename(previous)
        try:
            staging.rename(output)
        except OSError:
            if previous.exists():
                previous.rename(output)
            raise
