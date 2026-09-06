from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = BACKEND_ROOT / ".env"


def load_backend_environment(env_file: Path | None = None) -> bool:
    """Load backend configuration without overriding exported environment variables."""

    return load_dotenv(dotenv_path=env_file or DEFAULT_ENV_FILE, override=False)
