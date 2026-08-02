from __future__ import annotations

import warnings
from dataclasses import dataclass, replace
from enum import StrEnum, unique
from typing import TYPE_CHECKING, Final

from pyutilkit.term import SGRCodes, SGROutput, SGRString

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import PurePath


class NeonSSGWarning(UserWarning):
    """The category every warning-severity diagnostic is emitted under.

    Routing warnings through `warnings` rather than a channel of our own is what
    makes `-W error`, `PYTHONWARNINGS` and pytest's filters work on them without
    us inventing a parallel mechanism.
    """


@unique
class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@unique
class DiagnosticCode(StrEnum):
    BROKEN_LINK = "broken-link"
    BROKEN_ANCHOR = "broken-anchor"
    SNIPPET_OUTSIDE_ROOT = "snippet-outside-root"
    UNSAFE_OUTPUT_DIR = "unsafe-output-dir"
    PLUGIN_FAILED = "plugin-failed"
    INVALID_CONFIG_VALUE = "invalid-config-value"
    UNKNOWN_CONFIG_KEY = "unknown-config-key"
    MISSING_STEMMER = "missing-stemmer"
    MISSING_TRANSLATION = "missing-translation"
    DUPLICATE_URL = "duplicate-url"
    ORPHAN_PAGE = "orphan-page"


DEFAULT_SEVERITIES: Final[Mapping[DiagnosticCode, Severity]] = {
    DiagnosticCode.BROKEN_LINK: Severity.ERROR,
    DiagnosticCode.BROKEN_ANCHOR: Severity.ERROR,
    DiagnosticCode.SNIPPET_OUTSIDE_ROOT: Severity.ERROR,
    DiagnosticCode.UNSAFE_OUTPUT_DIR: Severity.ERROR,
    DiagnosticCode.PLUGIN_FAILED: Severity.ERROR,
    DiagnosticCode.INVALID_CONFIG_VALUE: Severity.ERROR,
    DiagnosticCode.UNKNOWN_CONFIG_KEY: Severity.WARNING,
    DiagnosticCode.MISSING_STEMMER: Severity.WARNING,
    DiagnosticCode.MISSING_TRANSLATION: Severity.WARNING,
    DiagnosticCode.DUPLICATE_URL: Severity.WARNING,
    DiagnosticCode.ORPHAN_PAGE: Severity.INFO,
}

SEVERITY_COLOURS: Final[Mapping[Severity, SGRCodes]] = {
    Severity.ERROR: SGRCodes.RED,
    Severity.WARNING: SGRCodes.YELLOW,
    Severity.INFO: SGRCodes.BLUE,
}


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: DiagnosticCode
    severity: Severity
    message: str
    source: PurePath | None = None
    line: int | None = None
    hint: str | None = None

    @property
    def location(self) -> str:
        if self.source is None:
            return ""

        location = self.source.as_posix()
        return location if self.line is None else f"{location}:{self.line}"

    @property
    def head(self) -> str:
        return f"{self.severity}[{self.code}]"

    def render(self) -> str:
        parts = (self.location, self.head, self.message)
        rendered = "  ".join(part for part in parts if part)
        return rendered if self.hint is None else f"{rendered}\n  hint: {self.hint}"

    def print(self) -> None:
        is_error = self.severity is Severity.ERROR
        strings = [
            SGRString(self.head, params=[SEVERITY_COLOURS[self.severity]]),
            SGRString(self.message),
        ]
        if self.location:
            strings.insert(0, SGRString(self.location))

        SGROutput(strings, is_error=is_error).print(sep="  ")
        if self.hint is not None:
            SGRString(
                f"  hint: {self.hint}",
                params=[SGRCodes.BLACK_BRIGHT],
                is_error=is_error,
            ).print()


def diagnostic(
    code: DiagnosticCode,
    message: str,
    *,
    source: PurePath | None = None,
    line: int | None = None,
    hint: str | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=DEFAULT_SEVERITIES[code],
        message=message,
        source=source,
        line=line,
        hint=hint,
    )


class DiagnosticCollector:
    __slots__ = ("_diagnostics", "strict")

    def __init__(self, *, strict: bool = False) -> None:
        self._diagnostics: list[Diagnostic] = []
        self.strict = strict

    def add(self, entry: Diagnostic) -> None:
        if self.strict and entry.severity is Severity.WARNING:
            entry = replace(entry, severity=Severity.ERROR)

        self._diagnostics.append(entry)
        if entry.severity is Severity.WARNING:
            warnings.warn(entry.render(), NeonSSGWarning, stacklevel=2)

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        return tuple(self._diagnostics)

    @property
    def errors(self) -> tuple[Diagnostic, ...]:
        return tuple(
            entry for entry in self._diagnostics if entry.severity is Severity.ERROR
        )

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    def render(self) -> str:
        return "\n".join(entry.render() for entry in self._diagnostics)

    def print_errors(self) -> None:
        for entry in self.errors:
            entry.print()
