from __future__ import annotations

import pytest

from neon_ssg.commands.base import BaseCommand


def test_stores_verbosity() -> None:
    assert BaseCommand(verbosity=2).verbosity == 2


def test_run_is_abstract() -> None:
    with pytest.raises(NotImplementedError):
        BaseCommand(verbosity=0).run()
