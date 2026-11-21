"""Anthropic client + model names. Messages API only (no betas)."""
from __future__ import annotations

import os

from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()
_client: AsyncAnthropic | None = None


def model_live() -> str:
    return os.environ.get("CLAUDE_MODEL_LIVE", "claude-sonnet-5-5")


def have_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        ws = os.environ.get("ANTHROPIC_WORKSPACE_ID")  # needed only for API keys not scoped to a workspace
        _client = AsyncAnthropic(max_retries=4, default_headers={"anthropic-workspace-id": ws} if ws else None)
    return _client
