from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from neon_ssg.commands.base import BaseCommand
from neon_ssg.lib.build import build
from neon_ssg.lib.config import resolve_config
from neon_ssg.lib.diagnostics import DiagnosticCollector
from neon_ssg.lib.exceptions import BuildFailedError
from neon_ssg.lib.loader import discover

if TYPE_CHECKING:
    from pathlib import Path


class BuildCommand(BaseCommand):
    __slots__ = ("site_root",)

    def __init__(self, verbosity: int, *, site_root: Path | None = None) -> None:
        super().__init__(verbosity)
        self.site_root = site_root

    def run(self) -> None:
        source = discover()
        collector = DiagnosticCollector()
        config = resolve_config(source, collector)
        if collector.has_errors:
            raise BuildFailedError(collector.render())
        if self.site_root is not None:
            config = replace(
                config, content=replace(config.content, site_root=self.site_root)
            )
        build(config, source.parser.data)
