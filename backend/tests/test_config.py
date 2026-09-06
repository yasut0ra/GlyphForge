from __future__ import annotations

import os

from app.config import load_backend_environment


def test_load_backend_environment_reads_dotenv_without_overriding_exported_values(
    tmp_path, monkeypatch
):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "GLYPHFORGE_TEST_FROM_FILE=loaded\nGLYPHFORGE_TEST_PRECEDENCE=from-file\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("GLYPHFORGE_TEST_FROM_FILE", raising=False)
    monkeypatch.setenv("GLYPHFORGE_TEST_PRECEDENCE", "exported")

    assert load_backend_environment(env_file)
    assert os.environ["GLYPHFORGE_TEST_FROM_FILE"] == "loaded"
    assert os.environ["GLYPHFORGE_TEST_PRECEDENCE"] == "exported"
