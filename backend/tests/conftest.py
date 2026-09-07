import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True)
def offline_tests(monkeypatch):
    # API-route imports load .env, but must never turn a test into a paid call.
    monkeypatch.setenv("OPENAI_API_KEY", "")
