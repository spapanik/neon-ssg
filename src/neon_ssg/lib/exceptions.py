from __future__ import annotations

from typing import ClassVar


class NeonSSGError(Exception):
    exit_code: ClassVar[int] = 1


class BuildFailedError(NeonSSGError):
    exit_code: ClassVar[int] = 1


class UnreadableConfigError(NeonSSGError):
    exit_code: ClassVar[int] = 2
