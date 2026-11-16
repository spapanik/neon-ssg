from __future__ import annotations

from threading import Event
from typing import TYPE_CHECKING
from unittest.mock import patch

from watchfiles import Change

from neon_ssg.lib.watcher import classify, watch_changes

if TYPE_CHECKING:
    from pathlib import Path


def test_classify_ignores_excluded_paths(tmp_path: Path) -> None:
    excluded = tmp_path / "output"
    paths = [tmp_path / ".git" / "config", excluded / "index.html"]
    assert classify(paths, [excluded]) == (False, False)
    assert classify([tmp_path / "docs" / "index.md"], [excluded]) == (True, False)
    assert classify([tmp_path / "uv.lock"], [excluded]) == (True, True)
    assert classify([excluded], [excluded]) == (False, False)


def test_watch_changes_notifies_once_per_relevant_batch(tmp_path: Path) -> None:
    events: list[bool] = []
    batches = [
        {(Change.modified, str(tmp_path / ".git" / "config"))},
        {(Change.modified, str(tmp_path / "index.md"))},
        {(Change.modified, str(tmp_path / "uv.lock"))},
    ]
    stop = Event()
    with patch("neon_ssg.lib.watcher.watch", return_value=iter(batches)) as watcher:
        watch_changes([tmp_path], [], stop, events.append)
    watcher.assert_called_once_with(str(tmp_path), stop_event=stop)
    assert events == [False, True]
