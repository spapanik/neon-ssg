from __future__ import annotations

import queue
import tempfile
import threading
from pathlib import Path

from pyutilkit.term import SGRString

from neon_ssg.commands.base import BaseCommand
from neon_ssg.lib.config import resolve_config
from neon_ssg.lib.devserver import PreviewServer
from neon_ssg.lib.diagnostics import DiagnosticCollector
from neon_ssg.lib.exceptions import NeonSSGError
from neon_ssg.lib.loader import discover
from neon_ssg.lib.preview import Preview
from neon_ssg.lib.watcher import watch_changes


def _watch_paths(root: Path) -> tuple[list[Path], list[Path]]:
    try:
        source = discover()
        config = resolve_config(source, DiagnosticCollector())
    except NeonSSGError:
        return [root], [root / "site"]
    paths = [root]
    docs = config.content.docs_root
    if docs.is_dir() and not docs.is_relative_to(root):
        paths.append(docs)
    content = source.parser.data.get("content", {})
    if isinstance(content, dict):
        entries = content.get("include", [])
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict) and isinstance(entry.get("src"), str):
                    parent = (docs / entry["src"]).resolve().parent
                    if parent.is_dir() and not any(
                        parent.is_relative_to(p) for p in paths
                    ):
                        paths.append(parent)
    return paths, [config.content.site_root]


class ServeCommand(BaseCommand):
    __slots__ = ("host", "port")

    def __init__(self, verbosity: int, host: str, port: int) -> None:
        super().__init__(verbosity)
        self.host = host
        self.port = port

    def run(self) -> None:
        root = Path.cwd().resolve()
        stop = threading.Event()
        events: queue.Queue[bool] = queue.Queue()
        with tempfile.TemporaryDirectory(prefix="neon-preview-") as tmp:
            preview = Preview(root, Path(tmp))
            server = PreviewServer((self.host, self.port), preview)
            paths, excluded = _watch_paths(root)

            def notify(dependencies: bool) -> None:  # noqa: FBT001
                preview.invalidate()
                events.put(dependencies)

            watcher = threading.Thread(
                target=watch_changes, args=(paths, excluded, stop, notify), daemon=True
            )
            http = threading.Thread(target=server.serve_forever, daemon=True)
            watcher.start()
            http.start()
            try:
                SGRString(
                    f"Serving on http://{self.host}:{server.server_port}/",
                    is_error=True,
                ).print()
                if not preview.rebuild() and preview.error:
                    SGRString(preview.error, is_error=True).print()
                sync_required = False
                while True:
                    dependencies = events.get()
                    while not events.empty():
                        dependencies |= events.get_nowait()
                    sync_required |= dependencies
                    if sync_required:
                        with preview.lock:
                            preview.error = (
                                "Dependencies changed; synchronise "
                                "and restart ssg serve."
                            )
                        SGRString(preview.error, is_error=True).print()
                    elif not preview.rebuild() and preview.error:
                        SGRString(preview.error, is_error=True).print()
            except KeyboardInterrupt:
                pass
            finally:
                stop.set()
                preview.stop()
                server.shutdown()
                server.server_close()
                watcher.join()
                http.join()
