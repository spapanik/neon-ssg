from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from neon_ssg.lib.coercers import as_bool, as_str
from neon_ssg.lib.exceptions import InvalidSettingTypeError

if TYPE_CHECKING:
    from collections.abc import Callable

COERCERS: list[Callable[[object], object]] = [as_str, as_bool]


@pytest.mark.parametrize("coerce", COERCERS)
def test_no_coercer_accepts_null(coerce: Callable[[object], object]) -> None:
    with pytest.raises(InvalidSettingTypeError) as exc_info:
        coerce(None)

    assert exc_info.value.value is None
    assert str(exc_info.value).endswith("got null")


def test_a_string_is_returned_unchanged() -> None:
    assert as_str("docs") == "docs"


@pytest.mark.parametrize("value", [1, 1.5, True, ["docs"], {"a": 1}])
def test_a_non_string_is_rejected(value: object) -> None:
    with pytest.raises(InvalidSettingTypeError) as exc_info:
        as_str(value)

    assert exc_info.value.expected == "a string"


def test_the_message_reads_with_a_key_in_front_of_it() -> None:
    with pytest.raises(InvalidSettingTypeError) as exc_info:
        as_str(None)

    assert f"'site.description' {exc_info.value}" == (
        "'site.description' expects a string, got null"
    )


@pytest.mark.parametrize("value", [True, False])
def test_a_real_boolean_survives(value: bool) -> None:
    assert as_bool(value) is value


@pytest.mark.parametrize("value", ["true", "TRUE", "True"])
def test_true_is_accepted_in_any_case(value: str) -> None:
    assert as_bool(value) is True


@pytest.mark.parametrize("value", ["false", "FALSE", "False"])
def test_false_is_accepted_in_any_case(value: str) -> None:
    assert as_bool(value) is False


@pytest.mark.parametrize(
    "value",
    [
        "yes",
        "no",
        "on",
        pytest.param("1", id="one-as-a-string"),
        pytest.param("0", id="zero-as-a-string"),
        pytest.param("", id="empty-string"),
        pytest.param(1, id="one"),
        pytest.param(0, id="zero"),
    ],
)
def test_no_other_spelling_of_a_boolean_is_accepted(value: object) -> None:
    with pytest.raises(InvalidSettingTypeError) as exc_info:
        as_bool(value)

    assert exc_info.value.expected == "a boolean"
