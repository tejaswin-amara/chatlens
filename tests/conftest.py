from datetime import datetime

import pytest

from src.utils import clock


@pytest.fixture
def frozen_clock(monkeypatch):
    def _freeze(iso: str):
        fixed = datetime.fromisoformat(iso)
        monkeypatch.setattr(clock, "now_ist", lambda: fixed.astimezone(clock.IST))

    return _freeze
