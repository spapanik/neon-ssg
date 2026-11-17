from __future__ import annotations

import json
import signal
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import chdir, closing
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from neon_ssg.commands.serve import ServeCommand, _watch_paths

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def test_stores_host_and_port() -> None:
    command = ServeCommand(verbosity=2, host="localhost", port=52467)
    assert command.verbosity == 2
    assert command.host == "localhost"
    assert command.port == 52467


def _until(check: Callable[[], bool]) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            if check():
                return
        except HTTPError as exc:
            exc.close()
        except (URLError, OSError, ValueError):
            pass
        time.sleep(0.05)
    msg = "Timed out waiting for preview state"
    raise AssertionError(msg)


def test_serve_rebuilds_and_recovers(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    page = docs / "index.md"
    page.write_text("# First", encoding="utf-8")
    with closing(socket.socket()) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as log:
        process = subprocess.Popen(  # noqa: S603
            [
                sys.executable,
                "-c",
                (
                    "import signal, sys; "
                    "signal.signal(signal.SIGINT, signal.default_int_handler); "
                    "signal.signal(signal.SIGBREAK, signal.default_int_handler) "
                    "if sys.platform == 'win32' else None; "
                    "from neon_ssg.commands.serve import ServeCommand; "
                    f"ServeCommand(0, '127.0.0.1', {port}).run()"
                ),
            ],
            cwd=tmp_path,
            stdout=subprocess.DEVNULL,
            stderr=log,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
        url = f"http://127.0.0.1:{port}"

        def get(path: str) -> bytes:
            with urlopen(url + path, timeout=1) as response:  # noqa: S310
                return cast("bytes", response.read())

        def status() -> dict[str, object]:
            return cast("dict[str, object]", json.loads(get("/__neon/status")))

        def extra_deleted() -> bool:
            try:
                get("/extra/")
            except HTTPError as exc:
                try:
                    return exc.code == 404
                finally:
                    exc.close()
            return False

        try:
            _until(lambda: cast("int", status()["revision"]) >= 1)
            assert b"First" in get("/")
            page.write_text("[Broken](missing.md)", encoding="utf-8")
            _until(lambda: status()["error"] is not None)
            assert b"First" in get("/")
            page.write_text("# Fixed", encoding="utf-8")
            _until(lambda: status()["error"] is None and b"Fixed" in get("/"))
            assert b"Fixed" in get("/")
            extra = docs / "extra.md"
            extra.write_text("# Extra", encoding="utf-8")
            _until(lambda: b"Extra" in get("/extra/"))
            assert b"Extra" in get("/extra/")
            before_delete = cast("int", status()["revision"])
            extra.unlink()
            _until(
                lambda: (
                    cast("int", status()["revision"]) > before_delete
                    and extra_deleted()
                )
            )
            (tmp_path / "uv.lock").write_text("changed", encoding="utf-8")
            _until(lambda: status()["error"] is not None)
            assert "restart" in str(status()["error"])
            assert not (tmp_path / "site").exists()
        finally:
            failure = sys.exception()
            try:
                if process.poll() is None:
                    process.send_signal(
                        getattr(signal, "CTRL_BREAK_EVENT", signal.SIGINT)
                        if sys.platform == "win32"
                        else signal.SIGINT
                    )
                    process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
                if failure is None:
                    raise
                failure.add_note("The preview also timed out during shutdown.")
            finally:
                log.seek(0)
                output = log.read()
                if failure is not None:
                    failure.add_note(f"Preview output:\n{output}")
        assert process.returncode == 0, output


def test_watch_paths_include_external_sources(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    docs = tmp_path / "manual"
    docs.mkdir()
    (project / "neon-ssg.yaml").write_text(
        "content:\n  docs_root: ../manual\n  site_root: public\n"
        "  include:\n    - src: ../LICENSE.md\n      as: LICENSE.md\n",
        encoding="utf-8",
    )
    with chdir(project):
        roots, excluded = _watch_paths(project)
    assert docs in roots
    assert excluded == [project / "public"]


def test_watch_paths_recovers_from_unreadable_config(tmp_path: Path) -> None:
    (tmp_path / "neon-ssg.yaml").write_text("[invalid", encoding="utf-8")
    with chdir(tmp_path):
        assert _watch_paths(tmp_path) == ([tmp_path], [tmp_path / "site"])


def test_supervisor_reports_errors_and_dependency_changes() -> None:
    preview = MagicMock()
    preview.rebuild.return_value = False
    preview.error = "broken"
    server = MagicMock()
    server.server_port = 1234
    events = MagicMock()
    events.get.side_effect = [False, True, KeyboardInterrupt]
    events.empty.return_value = True

    def watch(
        _paths: object,
        _excluded: object,
        _stop: object,
        notify: Callable[[bool], None],
    ) -> None:
        notify(False)  # noqa: FBT003

    with (
        patch("neon_ssg.commands.serve.Preview", return_value=preview),
        patch("neon_ssg.commands.serve.PreviewServer", return_value=server),
        patch("neon_ssg.commands.serve.queue.Queue", return_value=events),
        patch("neon_ssg.commands.serve.watch_changes", side_effect=watch),
    ):
        ServeCommand(0, "127.0.0.1", 0).run()
    assert preview.rebuild.call_count == 2
    preview.invalidate.assert_called_once()
    preview.stop.assert_called_once()
    server.shutdown.assert_called_once()
    server.server_close.assert_called_once()
    assert "restart" in preview.error


def test_watch_paths_handles_unfinished_include_configuration(tmp_path: Path) -> None:
    source = MagicMock()
    config = MagicMock()
    config.content.docs_root = tmp_path / "docs"
    config.content.site_root = tmp_path / "site"
    for content in (None, {"include": None}, {"include": [1, {}, {"src": "file"}]}):
        source.parser.data = {"content": content}
        with (
            patch("neon_ssg.commands.serve.discover", return_value=source),
            patch("neon_ssg.commands.serve.resolve_config", return_value=config),
        ):
            assert _watch_paths(tmp_path) == ([tmp_path], [tmp_path / "site"])


def test_supervisor_coalesces_edits_after_success() -> None:
    preview = MagicMock()
    preview.rebuild.return_value = True
    server = MagicMock()
    events = MagicMock()
    events.get.side_effect = [False, KeyboardInterrupt]
    events.empty.side_effect = [False, True]
    events.get_nowait.return_value = False
    with (
        patch("neon_ssg.commands.serve.Preview", return_value=preview),
        patch("neon_ssg.commands.serve.PreviewServer", return_value=server),
        patch("neon_ssg.commands.serve.queue.Queue", return_value=events),
        patch("neon_ssg.commands.serve.watch_changes"),
    ):
        ServeCommand(0, "127.0.0.1", 0).run()
    assert preview.rebuild.call_count == 2
