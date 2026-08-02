from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from neon_ssg.lib.coercers import as_str

if TYPE_CHECKING:
    from collections.abc import Callable


def non_empty(value: object) -> None:
    if not as_str(value).strip():
        msg = "must not be empty"
        raise ValueError(msg)


def absolute_url(value: object) -> None:
    url = as_str(value)
    split = urlsplit(url)
    if not split.scheme or not split.netloc:
        msg = f"must be an absolute URL, with a scheme and a host: {url!r}"
        raise ValueError(msg)


def within_root(value: object) -> None:
    path = as_str(value)
    pure = PurePosixPath(path)
    if pure.is_absolute():
        msg = f"must be a relative path: {path!r}"
        raise ValueError(msg)

    depth = 0
    for part in pure.parts:
        depth += -1 if part == ".." else 1
        if depth < 0:
            msg = f"must not escape its root: {path!r}"
            raise ValueError(msg)


def one_of(*allowed: str) -> Callable[[object], None]:
    options = ", ".join(repr(option) for option in allowed)

    def validator(value: object) -> None:
        if as_str(value) not in allowed:
            msg = f"must be one of {options}"
            raise ValueError(msg)

    return validator
