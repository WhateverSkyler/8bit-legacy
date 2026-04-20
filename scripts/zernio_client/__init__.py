from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parents[2] / "config" / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)

from .client import ZernioClient, ZernioError  # noqa: E402

__all__ = ["ZernioClient", "ZernioError"]
