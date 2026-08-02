from __future__ import annotations

import pytest

from neon_ssg.lib.exceptions import (
    BuildFailedError,
    NeonSSGError,
    UnreadableConfigError,
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
