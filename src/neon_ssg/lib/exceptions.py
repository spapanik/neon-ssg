from __future__ import annotations

from typing import ClassVar


class NeonSSGError(Exception):
    exit_code: ClassVar[int] = 1


class BuildFailedError(NeonSSGError):
    exit_code: ClassVar[int] = 1


class UnreadableConfigError(NeonSSGError):
    exit_code: ClassVar[int] = 2


class InvalidSettingTypeError(TypeError):
    def __init__(self, value: object, expected: str) -> None:
        super().__init__(f"expects {expected}, got {describe(value)}")
        self.value = value
        self.expected = expected


def describe(value: object) -> str:
    if value is None:
        return "null"

    if isinstance(value, (bool, int, float, str)):
        return repr(value)

    return type(value).__name__
