from __future__ import annotations

from typing import TYPE_CHECKING

from neon_ssg.commands.base import BaseCommand

if TYPE_CHECKING:
    from pathlib import Path


class BuildCommand(BaseCommand):
    __slots__ = ("site_root",)

    def __init__(self, verbosity: int, *, site_root: Path | None = None) -> None:
        super().__init__(verbosity)
        self.site_root = site_root

    def run(self) -> None:
        pass
