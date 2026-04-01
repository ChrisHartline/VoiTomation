"""
VoiTomation configuration.

All secrets come from environment variables or a .env file — never hardcoded.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Anthropic ──────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]
LILY_MODEL: str = os.getenv("LILY_MODEL", "claude-opus-4-6")

# ── GCP ───────────────────────────────────────────────────────────────────
GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "")
GCP_REGION: str = os.getenv("GCP_REGION", "us-central1")

# ── Ledger ────────────────────────────────────────────────────────────────
# Inc 1: SQLite hash-chain  |  Inc 2+: Hyperledger Fabric connection string
LEDGER_BACKEND: str = os.getenv("LEDGER_BACKEND", "sqlite")
LEDGER_DB_PATH: Path = Path(os.getenv("LEDGER_DB_PATH", "voitomation_audit.db"))
PERMISSIONS_FILE: Path = Path(os.getenv("PERMISSIONS_FILE", "permissions.yaml"))

# ── Governance ────────────────────────────────────────────────────────────
OPA_URL: str = os.getenv("OPA_URL", "http://localhost:8181")
POLICIES_DIR: Path = Path(os.getenv("POLICIES_DIR", "policies"))

# ── Voice auth ────────────────────────────────────────────────────────────
# Inc 1: stub (text input)  |  Inc 2: SpeechBrain  |  Inc 3: QC kernel
VOICE_AUTH_BACKEND: str = os.getenv("VOICE_AUTH_BACKEND", "stub")
