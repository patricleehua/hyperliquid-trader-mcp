"""
Configuration helpers for the Hyperliquid MCP trader.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final, Optional


def _load_env_file() -> None:
    """
    Lightweight .env loader to improve local DX without extra dependency.
    Only fills keys that are not already present in the environment.
    """
    project_root = Path(__file__).resolve().parent.parent
    env_file = project_root / ".env"
    if not env_file.exists():
        return

    for line in env_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        clean_key = key.strip()
        clean_value = _clean_env_value(value)

        if clean_key and clean_value and clean_key not in os.environ:
            os.environ[clean_key] = clean_value


def _clean_env_value(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    cleaned = raw.strip()
    if "#" in cleaned:
        cleaned = cleaned.split("#", 1)[0].strip()
    return cleaned or None


_load_env_file()


def _require_env(key: str) -> str:
    try:
        value = os.environ[key]
    except KeyError as exc:  # noqa: B904
        raise RuntimeError(
            f"Missing required environment variable '{key}'. "
            "Check your .env file or shell configuration."
        ) from exc

    cleaned = _clean_env_value(value)
    if not cleaned:
        raise RuntimeError(f"Environment variable '{key}' is empty.")
    return cleaned


ACCOUNT_ADDRESS: Final[str] = _require_env("HL_ACCOUNT_ADDRESS")
SECRET_KEY: Final[str] = _require_env("HL_SECRET_KEY")
_network_raw = _clean_env_value(os.getenv("HL_NETWORK"))
NETWORK: Final[str] = (_network_raw or "mainnet").lower()
API_BASE_URL: Final[str | None] = _clean_env_value(os.getenv("HL_API_BASE_URL"))
_skip_ws_raw = _clean_env_value(os.getenv("HL_SKIP_WS"))
SKIP_WEBSOCKET: Final[bool] = (_skip_ws_raw or "false").lower() in {
    "1",
    "true",
    "yes",
}

# Optional HTTP guard: require MCP requests to send a specific header/value pair.
_header_value_raw = _clean_env_value(os.getenv("MCP_AUTH_HEADER_VALUE"))
REQUEST_HEADER_VALUE: Final[str | None] = _header_value_raw
_header_name_raw = _clean_env_value(os.getenv("MCP_AUTH_HEADER_NAME"))
REQUEST_HEADER_NAME: Final[str] = _header_name_raw or "Authorization"
