from __future__ import annotations

import pytest

from neon_ssg.lib.exceptions import (
    BuildFailedError,
    InvalidSettingTypeError,
    NeonSSGError,
    UnreadableConfigError,
    describe,
)


def test_a_failed_build_exits_one() -> None:
    assert BuildFailedError.exit_code == 1


def test_an_unreadable_config_exits_two() -> None:
    assert UnreadableConfigError.exit_code == 2


def test_the_base_defaults_to_one() -> None:
    assert NeonSSGError.exit_code == 1


@pytest.mark.parametrize("error", [BuildFailedError, UnreadableConfigError])
def test_every_error_is_catchable_as_the_base(error: type[NeonSSGError]) -> None:
    msg = "something went wrong"
    with pytest.raises(NeonSSGError) as exc_info:
        raise error(msg)

    assert exc_info.value.exit_code == error.exit_code
    assert str(exc_info.value) == msg


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "null"),
        (True, "True"),
        (2, "2"),
        (1.5, "1.5"),
        ("docs", "'docs'"),
        (["docs"], "list"),
        ({"docs": 1}, "dict"),
    ],
)
def test_a_value_is_described_as_the_user_wrote_it(
    value: object, expected: str
) -> None:
    assert describe(value) == expected


def test_an_invalid_type_carries_the_value_and_the_expectation() -> None:
    error = InvalidSettingTypeError(None, "a string")

    assert error.value is None
    assert error.expected == "a string"
    assert str(error) == "expects a string, got null"


def test_an_invalid_type_is_catchable_as_a_type_error() -> None:
    with pytest.raises(TypeError):
        raise InvalidSettingTypeError(2, "a string")
