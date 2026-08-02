from __future__ import annotations

from neon_ssg.commands.base import BaseCommand


class ServeCommand(BaseCommand):
    __slots__ = ("host", "port")

    def __init__(self, verbosity: int, host: str, port: int) -> None:
        super().__init__(verbosity)
        self.host = host
        self.port = port

    def run(self) -> None:
        pass
