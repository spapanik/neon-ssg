from __future__ import annotations

import json
import threading
from contextlib import chdir
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from neon_ssg.commands.build import BuildCommand
from neon_ssg.lib.devserver import SCRIPT, PreviewServer
from neon_ssg.lib.preview import Preview

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def server(tmp_path: Path) -> Iterator[tuple[Preview, str]]:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "index.md").write_text("# Hello", encoding="utf-8")
    (tmp_path / "docs" / "asset.txt").write_text("asset", encoding="utf-8")
    generations = tmp_path / "generations"
    generations.mkdir()
    preview = Preview(tmp_path, generations)
    http = PreviewServer(("127.0.0.1", 0), preview)
    thread = threading.Thread(target=http.serve_forever)
    thread.start()
    try:
        yield preview, f"http://127.0.0.1:{http.server_port}"
    finally:
        http.shutdown()
        http.server_close()
        thread.join()


def test_preview_serves_identical_build_and_injects_reload(
    server: tuple[Preview, str], tmp_path: Path
) -> None:
    preview, url = server
    with chdir(tmp_path):
        BuildCommand(0).run()
    assert preview.rebuild()
    with urlopen(url + "/", timeout=3) as response:  # noqa: S310
        html = response.read()
    assert html == (tmp_path / "site" / "index.html").read_bytes() + SCRIPT
    with urlopen(url + "/asset.txt", timeout=3) as response:  # noqa: S310
        assert response.read() == b"asset"
    with urlopen(url + "/__neon/status", timeout=3) as response:  # noqa: S310
        assert json.load(response) == {"revision": 1, "error": None}
    with pytest.raises(HTTPError) as exc, urlopen(url + "/missing", timeout=3):  # noqa: S310
        pass
    assert exc.value.code == 404


def test_waiting_and_unsafe_path(server: tuple[Preview, str]) -> None:
    preview, url = server
    with urlopen(url + "/", timeout=3) as response:  # noqa: S310
        assert b"Waiting for a successful build" in response.read()
    preview.error = "Broken configuration"
    with urlopen(url + "/__neon/status", timeout=3) as response:  # noqa: S310
        assert json.load(response)["error"] == "Broken configuration"
    with pytest.raises(HTTPError) as exc, urlopen(url + "/%2e%2e/secret", timeout=3):  # noqa: S310
        pass
    assert exc.value.code == 404


def test_resolved_path_outside_generation_is_rejected(
    server: tuple[Preview, str], tmp_path: Path
) -> None:
    preview, url = server
    assert preview.rebuild()
    with (
        patch.object(Path, "is_relative_to", return_value=False),
        pytest.raises(HTTPError) as exc,
        urlopen(url + "/asset.txt", timeout=3),  # noqa: S310
    ):
        pass
    assert exc.value.code == 404
    assert tmp_path.exists()
