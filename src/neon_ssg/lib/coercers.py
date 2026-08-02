from __future__ import annotations

from neon_ssg.lib.exceptions import InvalidSettingTypeError

TRUE = "true"
FALSE = "false"


def as_str(value: object) -> str:
    if isinstance(value, str):
        return value

    raise InvalidSettingTypeError(value, "a string")


def as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        lowered = value.casefold()
        if lowered == TRUE:
            return True
        if lowered == FALSE:
            return False

    raise InvalidSettingTypeError(value, "a boolean")
