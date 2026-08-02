from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from neon_ssg.lib.exceptions import InvalidSettingTypeError
from neon_ssg.lib.validators import absolute_url, non_empty, one_of, within_root

if TYPE_CHECKING:
    from collections.abc import Callable


def test_a_filled_string_passes() -> None:
    non_empty("neon-ssg")


@pytest.mark.parametrize("value", ["", " ", "\t\n"])
def test_an_empty_string_is_rejected(value: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        non_empty(value)


def test_a_validator_message_reads_with_a_key_in_front_of_it() -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        non_empty("  ")

    assert f"'site.name' {exc_info.value}" == "'site.name' must not be empty"


@pytest.mark.parametrize(
    "url", ["https://example.com/docs/", "http://localhost:52467/", "https://a.io"]
)
def test_an_absolute_url_passes(url: str) -> None:
    absolute_url(url)


@pytest.mark.parametrize("url", ["example.com", "/docs/", "", "docs/index.md"])
def test_a_url_without_a_scheme_and_a_host_is_rejected(url: str) -> None:
    with pytest.raises(ValueError, match="must be an absolute URL"):
        absolute_url(url)


@pytest.mark.parametrize("path", ["a/b/c.md", "a/../b.md", "index.md", "./a/b.md"])
def test_a_contained_path_passes(path: str) -> None:
    within_root(path)


@pytest.mark.parametrize("path", ["../secrets.md", "a/../../b", "../../../etc/passwd"])
def test_an_escaping_path_is_rejected(path: str) -> None:
    with pytest.raises(ValueError, match="must not escape its root"):
        within_root(path)


@pytest.mark.parametrize("path", ["/etc/passwd", "/"])
def test_an_absolute_path_is_rejected(path: str) -> None:
    with pytest.raises(ValueError, match="must be a relative path"):
        within_root(path)


def test_a_listed_value_passes() -> None:
    one_of("git", "json")("git")


def test_an_unlisted_value_is_rejected_and_names_the_options() -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        one_of("git", "json")("svn")

    assert f"'versions.provider' {exc_info.value}" == (
        "'versions.provider' must be one of 'git', 'json'"
    )


@pytest.mark.parametrize(
    "validate", [non_empty, absolute_url, within_root, one_of("git")]
)
def test_every_validator_rejects_a_non_string(
    validate: Callable[[object], None],
) -> None:
    with pytest.raises(InvalidSettingTypeError):
        validate(None)
