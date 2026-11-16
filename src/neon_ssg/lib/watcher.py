"""File watching boundary for the development supervisor."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from watchfiles import watch

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from threading import Event

EXCLUDED = frozenset(
    {
        ".venv",
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".cov_cache",
    }
)
DEPENDENCIES = frozenset({"pyproject.toml", "uv.lock"})


def classify(
    paths: Iterable[Path], excluded_roots: Iterable[Path]
) -> tuple[bool, bool]:
    """Return whether relevant input and dependency metadata changed."""
    roots = tuple(root.resolve() for root in excluded_roots)
    relevant = False
    dependencies = False
    for path in paths:
        resolved = path.resolve()
        if any(part in EXCLUDED for part in resolved.parts) or any(
            resolved == root or root in resolved.parents for root in roots
        ):
            continue
        relevant = True
        dependencies |= resolved.name in DEPENDENCIES
    return relevant, dependencies


def watch_changes(
    roots: Iterable[Path],
    excluded_roots: Iterable[Path],
    stop: Event,
    notify: Callable[[bool], None],
) -> None:
    """Watch inputs until stopped and coalesce each batch into one event."""
    watched = tuple(str(root) for root in roots)
    excluded = tuple(excluded_roots)
    for changes in watch(*watched, stop_event=stop):
        relevant, dependencies = classify((Path(name) for _, name in changes), excluded)
        if relevant:
            notify(dependencies)
