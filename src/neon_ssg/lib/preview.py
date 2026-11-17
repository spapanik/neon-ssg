"""Manage isolated, replaceable generations of a development preview."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable


T = TypeVar("T")


class Preview:
    """Build generations in a worker and publish only successful output."""

    def __init__(self, root: Path, temporary_root: Path) -> None:
        self.root = root
        self.temporary_root = temporary_root
        self.lock = threading.RLock()
        self.current: Path | None = None
        self.revision = 0
        self.error: str | None = None
        self.process: subprocess.Popen[str] | None = None
        self.stopping = False

    def rebuild(self) -> bool:
        generation = Path(
            tempfile.mkdtemp(prefix="generation-", dir=self.temporary_root)
        )
        output = generation / "site"
        with self.lock:
            if self.stopping:
                shutil.rmtree(generation)
                return False
            self.process = subprocess.Popen(  # noqa: S603
                [sys.executable, "-m", "neon_ssg.preview_worker", str(output)],
                cwd=self.root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            process = self.process
        result, _ = process.communicate()
        with self.lock:
            self.process = None
            if process.returncode != 0 or self.stopping:
                self.error = result.strip() or "Build failed"
                shutil.rmtree(generation)
                return False
            previous = self.current
            self.current = output
            self.error = None
            self.revision += 1
            if previous is not None:
                shutil.rmtree(previous.parent)
            return True

    def read(self, reader: Callable[[Path], T]) -> T | None:
        """Keep the selected generation alive until the read finishes."""
        with self.lock:
            return None if self.current is None else reader(self.current)

    def stop(self) -> None:
        with self.lock:
            self.stopping = True
            if self.process is not None:
                self.process.terminate()
