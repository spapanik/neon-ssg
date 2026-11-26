from __future__ import annotations

import importlib
import runpy
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from neon_ssg.lib.exceptions import BuildFailedError
from neon_ssg.lib.preview import Preview

if TYPE_CHECKING:
    from pathlib import Path


def test_preview_keeps_last_successful_generation(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    page = docs / "index.md"
    page.write_text("# First", encoding="utf-8")
    output = tmp_path / "generations"
    output.mkdir()
    preview = Preview(tmp_path, output)
    assert preview.rebuild()
    previous = preview.current
    assert previous is not None
    assert previous.parent.parent == output
    assert previous.name == "site"
    assert preview.revision == 1
    assert b"First" in (previous / "index.html").read_bytes()
    page.write_text("[Broken](missing.md)", encoding="utf-8")
    assert not preview.rebuild()
    assert preview.current == previous
    failure = preview.error
    assert failure is not None
    assert b"First" in (previous / "index.html").read_bytes()
    page.write_text("# Fixed", encoding="utf-8")
    assert preview.rebuild()
    current = preview.current
    assert current is not None
    assert current != previous
    assert current.parent.parent == output
    assert current.name == "site"
    assert b"Fixed" in (current / "index.html").read_bytes()
    assert preview.revision == 2
    assert preview.error is None
    assert not previous.exists()
    preview.stop()
    assert not preview.rebuild()


def test_stop_terminates_active_worker(tmp_path: Path) -> None:
    preview = Preview(tmp_path, tmp_path)
    process = MagicMock()
    preview.process = process
    preview.stop()
    process.terminate.assert_called_once()


def test_worker_entry_point(tmp_path: Path) -> None:
    with (
        patch("sys.argv", ["neon_ssg.preview_worker", str(tmp_path / "site")]),
        patch("neon_ssg.commands.build.BuildCommand") as command,
    ):
        runpy.run_module("neon_ssg.preview_worker", run_name="__main__")
    command.assert_called_once_with(verbosity=0, site_root=tmp_path / "site")
    command.return_value.run.assert_called_once_with()


def test_worker_can_be_imported() -> None:
    result = runpy.run_module("neon_ssg.preview_worker")
    assert callable(result["main"])


def test_inflight_build_is_discarded_after_edit(tmp_path: Path) -> None:
    preview = Preview(tmp_path, tmp_path)
    process = MagicMock()
    process.returncode = 0

    def communicate() -> tuple[str, None]:
        preview.invalidate()
        return "", None

    process.communicate.side_effect = communicate
    with patch("neon_ssg.lib.preview.subprocess.Popen", return_value=process):
        assert not preview.rebuild()
    assert preview.current is None
    assert preview.revision == 0


def test_interrupted_worker_is_terminated_and_reaped(tmp_path: Path) -> None:
    preview = Preview(tmp_path, tmp_path)
    process = MagicMock()
    process.communicate.side_effect = [KeyboardInterrupt, ("", None)]
    with (
        patch("neon_ssg.lib.preview.subprocess.Popen", return_value=process),
        pytest.raises(KeyboardInterrupt),
    ):
        preview.rebuild()
    process.terminate.assert_called_once()
    assert process.communicate.call_count == 2
    assert preview.process is None


def test_worker_reports_build_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with (
        patch("sys.argv", ["preview_worker", str(tmp_path)]),
        patch(
            "neon_ssg.preview_worker.BuildCommand", side_effect=BuildFailedError("bad")
        ),
        pytest.raises(SystemExit, match="1"),
    ):
        importlib.import_module("neon_ssg.preview_worker").main()
    assert capsys.readouterr().err == "bad\n"


def test_preview_builds_default_translation(tmp_path: Path) -> None:
    (tmp_path / "docs/en-gb").mkdir(parents=True)
    (tmp_path / "docs/en-gb/index.md").write_text("# Hello", encoding="utf-8")
    (tmp_path / "neon-ssg.yaml").write_text(
        "translations:\n  default:\n    - name: English\n"
        "      path: en-gb\n      link: en\n      lang: en\n"
        "  alternate:\n    - link: missing\n",
        encoding="utf-8",
    )
    output = tmp_path / "generations"
    output.mkdir()
    preview = Preview(tmp_path, output)
    assert preview.rebuild(), preview.error
    assert preview.current is not None
    assert "Hello" in (preview.current / "en/index.html").read_text(encoding="utf-8")
    assert 'href="en/"' in (preview.current / "index.html").read_text(encoding="utf-8")
    preview.stop()
