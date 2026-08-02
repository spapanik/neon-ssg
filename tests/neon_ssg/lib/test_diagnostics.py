from __future__ import annotations

import warnings
from pathlib import PurePosixPath, PureWindowsPath

import pytest

from neon_ssg.lib.diagnostics import (
    DEFAULT_SEVERITIES,
    SEVERITY_COLOURS,
    Diagnostic,
    DiagnosticCode,
    DiagnosticCollector,
    NeonSSGWarning,
    Severity,
    diagnostic,
)

ERROR_CODES = frozenset(
    {
        DiagnosticCode.BROKEN_LINK,
        DiagnosticCode.BROKEN_ANCHOR,
        DiagnosticCode.SNIPPET_OUTSIDE_ROOT,
        DiagnosticCode.UNSAFE_OUTPUT_DIR,
        DiagnosticCode.PLUGIN_FAILED,
        DiagnosticCode.INVALID_CONFIG_VALUE,
    }
)
WARNING_CODES = frozenset(
    {
        DiagnosticCode.UNKNOWN_CONFIG_KEY,
        DiagnosticCode.MISSING_STEMMER,
        DiagnosticCode.MISSING_TRANSLATION,
        DiagnosticCode.DUPLICATE_URL,
    }
)
INFO_CODES = frozenset({DiagnosticCode.ORPHAN_PAGE})


def _by_severity(severity: Severity) -> frozenset[DiagnosticCode]:
    return frozenset(
        code for code, value in DEFAULT_SEVERITIES.items() if value is severity
    )


def test_every_code_has_a_default_severity() -> None:
    assert set(DEFAULT_SEVERITIES) == set(DiagnosticCode)


def test_the_severity_table_matches_the_spec() -> None:
    assert _by_severity(Severity.ERROR) == ERROR_CODES
    assert _by_severity(Severity.WARNING) == WARNING_CODES
    assert _by_severity(Severity.INFO) == INFO_CODES


def test_every_severity_is_visually_distinguishable() -> None:
    assert set(SEVERITY_COLOURS) == set(Severity)
    assert len(set(SEVERITY_COLOURS.values())) == len(Severity)


def test_a_full_diagnostic_renders_in_the_specified_format() -> None:
    entry = diagnostic(
        DiagnosticCode.BROKEN_LINK,
        "no such page: 'usage/intro.md'",
        source=PurePosixPath("docs/usage/index.md"),
        line=42,
        hint="did you mean 'usage/index.md'?",
    )

    assert entry.render() == (
        "docs/usage/index.md:42  error[broken-link]  no such page: 'usage/intro.md'"
        "\n  hint: did you mean 'usage/index.md'?"
    )


def test_a_bare_diagnostic_renders_as_head_and_message() -> None:
    entry = diagnostic(DiagnosticCode.ORPHAN_PAGE, "not reachable from the nav")

    assert entry.render() == "info[orphan-page]  not reachable from the nav"


def test_a_source_without_a_line_renders_without_a_position() -> None:
    entry = diagnostic(
        DiagnosticCode.DUPLICATE_URL,
        "two sources, one URL",
        source=PurePosixPath("docs/guide.md"),
    )

    assert (
        entry.render() == "docs/guide.md  warning[duplicate-url]  two sources, one URL"
    )


def test_a_hint_survives_without_a_source() -> None:
    entry = diagnostic(
        DiagnosticCode.UNKNOWN_CONFIG_KEY,
        "unknown configuration key: 'sight'",
        hint="did you mean 'site'?",
    )

    assert entry.render() == (
        "warning[unknown-config-key]  unknown configuration key: 'sight'"
        "\n  hint: did you mean 'site'?"
    )


def test_a_windows_path_renders_with_forward_slashes() -> None:
    entry = diagnostic(
        DiagnosticCode.BROKEN_ANCHOR,
        "no such anchor",
        source=PureWindowsPath(r"docs\usage\index.md"),
        line=7,
    )

    assert entry.location == "docs/usage/index.md:7"


def test_a_diagnostic_takes_its_severity_from_its_code() -> None:
    assert diagnostic(DiagnosticCode.PLUGIN_FAILED, "boom").severity is Severity.ERROR
    assert (
        diagnostic(DiagnosticCode.MISSING_STEMMER, "no stemmer").severity
        is Severity.WARNING
    )


def test_a_diagnostic_is_frozen() -> None:
    entry = diagnostic(DiagnosticCode.BROKEN_LINK, "no such page")

    with pytest.raises(AttributeError):
        entry.message = "something else"  # type: ignore[misc]  # ty: ignore[invalid-assignment]


def test_an_error_is_printed_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    diagnostic(
        DiagnosticCode.BROKEN_LINK,
        "no such page: 'usage/intro.md'",
        source=PurePosixPath("docs/usage/index.md"),
        line=42,
    ).print()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "docs/usage/index.md:42  error[broken-link]  no such page: 'usage/intro.md'\n"
    )


def test_a_warning_is_printed_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    diagnostic(DiagnosticCode.DUPLICATE_URL, "two sources, one URL").print()

    captured = capsys.readouterr()
    assert captured.out == "warning[duplicate-url]  two sources, one URL\n"
    assert captured.err == ""


def test_a_printed_hint_gets_its_own_line(capsys: pytest.CaptureFixture[str]) -> None:
    diagnostic(
        DiagnosticCode.UNKNOWN_CONFIG_KEY,
        "unknown configuration key: 'sight'",
        hint="did you mean 'site'?",
    ).print()

    assert capsys.readouterr().out == (
        "warning[unknown-config-key]  unknown configuration key: 'sight'\n"
        "  hint: did you mean 'site'?\n"
    )


def test_an_empty_collector_has_nothing_to_report() -> None:
    collector = DiagnosticCollector()

    assert collector.diagnostics == ()
    assert collector.errors == ()
    assert collector.has_errors is False
    assert collector.render() == ""


def test_an_error_makes_the_collector_report_failure() -> None:
    collector = DiagnosticCollector()

    collector.add(diagnostic(DiagnosticCode.INVALID_CONFIG_VALUE, "wrong type"))

    assert collector.has_errors is True
    assert len(collector.errors) == 1


def test_warnings_alone_do_not_make_a_run_fail() -> None:
    collector = DiagnosticCollector()

    with pytest.warns(NeonSSGWarning):
        collector.add(diagnostic(DiagnosticCode.DUPLICATE_URL, "two sources, one URL"))
    collector.add(diagnostic(DiagnosticCode.ORPHAN_PAGE, "unreachable"))

    assert collector.has_errors is False
    assert len(collector.diagnostics) == 2


def test_recording_a_warning_emits_the_warning_category() -> None:
    collector = DiagnosticCollector()
    entry = diagnostic(DiagnosticCode.MISSING_STEMMER, "no stemmer for 'xx'")

    with pytest.warns(NeonSSGWarning) as recorded:
        collector.add(entry)

    assert len(recorded) == 1
    assert str(recorded[0].message) == entry.render()


def test_an_error_is_not_emitted_as_a_warning() -> None:
    collector = DiagnosticCollector()

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        collector.add(diagnostic(DiagnosticCode.BROKEN_LINK, "no such page"))
        collector.add(diagnostic(DiagnosticCode.ORPHAN_PAGE, "unreachable"))

    assert recorded == []


def test_strict_promotes_a_warning_to_an_error() -> None:
    collector = DiagnosticCollector(strict=True)

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        collector.add(diagnostic(DiagnosticCode.UNKNOWN_CONFIG_KEY, "unknown key"))

    assert collector.has_errors is True
    assert collector.diagnostics[0].severity is Severity.ERROR
    assert recorded == [], "a promoted warning is an error, and is reported as one"


def test_strict_leaves_info_alone() -> None:
    collector = DiagnosticCollector(strict=True)

    collector.add(diagnostic(DiagnosticCode.ORPHAN_PAGE, "unreachable"))

    assert collector.has_errors is False
    assert collector.diagnostics[0].severity is Severity.INFO


def test_the_collector_renders_every_diagnostic_it_holds() -> None:
    collector = DiagnosticCollector()
    error = diagnostic(DiagnosticCode.BROKEN_LINK, "no such page")
    info = diagnostic(DiagnosticCode.ORPHAN_PAGE, "unreachable")

    collector.add(error)
    collector.add(info)

    assert collector.render() == f"{error.render()}\n{info.render()}"


def test_only_errors_are_printed_as_errors(
    capsys: pytest.CaptureFixture[str],
) -> None:
    collector = DiagnosticCollector()

    collector.add(diagnostic(DiagnosticCode.BROKEN_LINK, "no such page"))
    collector.add(diagnostic(DiagnosticCode.ORPHAN_PAGE, "unreachable"))
    capsys.readouterr()

    collector.print_errors()

    captured = capsys.readouterr()
    assert captured.err == "error[broken-link]  no such page\n"
    assert captured.out == ""


def test_a_diagnostic_can_be_built_directly_with_an_explicit_severity() -> None:
    entry = Diagnostic(
        code=DiagnosticCode.UNKNOWN_CONFIG_KEY,
        severity=Severity.ERROR,
        message="unknown key",
    )

    assert entry.head == "error[unknown-config-key]"
