"""
Remote model inference via Fireworks AI.
Every token here is counted toward the competition score — use sparingly.

All calls MUST go through FIREWORKS_BASE_URL — the harness's metering/judging
proxy. Calls that bypass it are not recorded and score zero.
"""

import os
import time
from dataclasses import dataclass, field

from agent.config import (
    FIREWORKS_API_KEY,
    FIREWORKS_BASE_URL,
    REMOTE_MODEL_FAST,
    REMOTE_MODEL_STRONG,
    REMOTE_MAX_TOKENS,
    REMOTE_TIMEOUT,
)


@dataclass
class RemoteResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency: float
    model: str
    success: bool
    error: str = ""


# Session-level token counter
_session_tokens: dict[str, int] = {"prompt": 0, "completion": 0, "total": 0}


def get_session_tokens() -> dict[str, int]:
    return dict(_session_tokens)


def reset_session_tokens() -> None:
    _session_tokens.update({"prompt": 0, "completion": 0, "total": 0})


def run(
    query: str,
    *,
    use_strong_model: bool = False,
    system: str = "You are a helpful, accurate, and concise assistant.",
) -> RemoteResult:
    """
    Call Fireworks AI.

    use_strong_model=True → use the larger/more capable model (more tokens).
    Default: use the fast/cheap model.
    """
    if not FIREWORKS_API_KEY:
        return RemoteResult(
            text="", prompt_tokens=0, completion_tokens=0, total_tokens=0,
            latency=0.0, model="", success=False,
            error="FIREWORKS_API_KEY not set in .env",
        )

    try:
        from fireworks.client import Fireworks  # type: ignore
    except ImportError:
        return RemoteResult(
            text="", prompt_tokens=0, completion_tokens=0, total_tokens=0,
            latency=0.0, model="", success=False,
            error="fireworks-ai not installed — run: pip install fireworks-ai",
        )

    model = REMOTE_MODEL_STRONG if use_strong_model else REMOTE_MODEL_FAST
    client = Fireworks(api_key=FIREWORKS_API_KEY, base_url=FIREWORKS_BASE_URL, timeout=REMOTE_TIMEOUT)

    t0 = time.time()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": query},
            ],
            max_tokens=REMOTE_MAX_TOKENS,
            temperature=0.1,
        )
    except Exception as exc:
        return RemoteResult(
            text="", prompt_tokens=0, completion_tokens=0, total_tokens=0,
            latency=time.time() - t0, model=model, success=False,
            error=str(exc),
        )

    latency = time.time() - t0
    text = resp.choices[0].message.content.strip()
    usage = resp.usage

    pt = usage.prompt_tokens
    ct = usage.completion_tokens
    tt = usage.total_tokens

    _session_tokens["prompt"] += pt
    _session_tokens["completion"] += ct
    _session_tokens["total"] += tt

    return RemoteResult(
        text=text,
        prompt_tokens=pt,
        completion_tokens=ct,
        total_tokens=tt,
        latency=latency,
        model=model,
        success=True,
    )
