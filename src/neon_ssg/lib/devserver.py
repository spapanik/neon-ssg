"""HTTP transport for development previews."""

from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, cast
from urllib.parse import unquote, urlsplit

if TYPE_CHECKING:
    from pathlib import Path

    from neon_ssg.lib.preview import Preview

SCRIPT = b"""<script>
let revision = null;
async function poll() {
  try {
    const status = await (await fetch('/__neon/status', {cache:'no-store'})).json();
    let error = document.getElementById('__neon_error');
    if (status.error) {
      if (!error) {
        error = document.createElement('pre'); error.id = '__neon_error';
        error.style.cssText = 'position:fixed;inset:0;z-index:9999;overflow:auto;'
          + 'background:#300;color:white;padding:2em';
        document.body.appendChild(error);
      }
      error.textContent = status.error;
    } else if (error) error.remove();
    if (revision !== null && revision !== status.revision) location.reload();
    revision = status.revision;
  } catch (_) {}
  setTimeout(poll, 500);
}
poll();
</script>"""


class PreviewServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], preview: Preview) -> None:
        self.preview = preview
        super().__init__(address, PreviewHandler)


class PreviewHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        server = cast("PreviewServer", self.server)
        path = urlsplit(self.path).path
        if path == "/__neon/status":
            with server.preview.lock:
                payload = json.dumps(
                    {"revision": server.preview.revision, "error": server.preview.error}
                ).encode("utf-8")
            self._send("application/json", payload)
            return
        relative = PurePosixPath(unquote(path).lstrip("/"))
        if ".." in relative.parts or "\\" in str(relative):
            self.send_error(404)
            return

        def read(root: Path) -> tuple[bytes, str]:
            target = (root / relative).resolve()
            if not target.is_relative_to(root):
                raise FileNotFoundError
            if target.is_dir():
                target = target / "index.html"
            return target.read_bytes(), mimetypes.guess_type(target.name)[
                0
            ] or "application/octet-stream"

        try:
            result = server.preview.read(read)
        except (OSError, ValueError):
            self.send_error(404)
            return
        if result is None:
            payload, content_type = (
                (
                    b"<!doctype html><html><body>"
                    b"Waiting for a successful build.</body></html>"
                ),
                "text/html",
            )
        else:
            payload, content_type = result
        if content_type == "text/html":
            payload += SCRIPT
        self._send(content_type, payload)

    def _send(self, content_type: str, payload: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)
