import os
from pathlib import Path

from dotenv import load_dotenv


# Repository root:
# agent-auth-lab/
ROOT_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT_DIR / "data"
RUN_DIR = ROOT_DIR / ".run"

DATA_DIR.mkdir(exist_ok=True)
RUN_DIR.mkdir(exist_ok=True)

load_dotenv(ROOT_DIR / ".env")


KC_BASE_URL = os.getenv(
    "KC_BASE_URL",
    "http://127.0.0.1:8080",
)

KC_REALM = os.getenv(
    "KC_REALM",
    "agent-lab",
)

ISSUER = f"{KC_BASE_URL}/realms/{KC_REALM}"

AUDIT_DB = DATA_DIR / "audit.db"
