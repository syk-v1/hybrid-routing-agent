"""
Local model inference via Ollama.
All tokens here cost ZERO toward the competition score.
"""

import time
import requests
from dataclasses import dataclass

from agent.config import LOCAL_MODEL, LOCAL_BASE_URL, LOCAL_TIMEOUT


@dataclass
class LocalResult:
    text: str
    confidence: float   # 0–1, from output_confidence heuristic
    latency: float      # seconds
    success: bool
    error: str = ""


def _call_ollama(prompt: str, system: str = "") -> tuple[str, float]:
    """Raw Ollama /api/generate call. Returns (text, latency_seconds)."""
    url = f"{LOCAL_BASE_URL}/api/generate"
    payload = {
        "model": LOCAL_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,   # deterministic for accuracy
            "num_predict": 1024,
        },
    }
    if system:
        payload["system"] = system

    t0 = time.time()
    resp = requests.post(url, json=payload, timeout=LOCAL_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", "").strip(), time.time() - t0


def run(query: str) -> LocalResult:
    """Run query on local model, return result with confidence."""
    from agent.router import output_confidence

    try:
        text, latency = _call_ollama(query)
        conf = output_confidence(text)
        return LocalResult(text=text, confidence=conf, latency=latency, success=True)
    except requests.exceptions.ConnectionError:
        return LocalResult(
            text="", confidence=0.0, latency=0.0, success=False,
            error="Ollama not running – start with: ollama serve",
        )
    except requests.exceptions.Timeout:
        return LocalResult(
            text="", confidence=0.0, latency=LOCAL_TIMEOUT, success=False,
            error="Local model timed out",
        )
    except Exception as exc:
        return LocalResult(
            text="", confidence=0.0, latency=0.0, success=False,
            error=str(exc),
        )


def is_available() -> bool:
    """Check if Ollama is running and the local model is pulled."""
    try:
        resp = requests.get(f"{LOCAL_BASE_URL}/api/tags", timeout=5)
        tags = resp.json().get("models", [])
        return any(LOCAL_MODEL in m.get("name", "") for m in tags)
    except Exception:
        return False


def pull_model_if_needed() -> None:
    """Pull the local model if not already available."""
    if is_available():
        return
    print(f"[local] Pulling model {LOCAL_MODEL!r} — this may take a few minutes...")
    requests.post(
        f"{LOCAL_BASE_URL}/api/pull",
        json={"name": LOCAL_MODEL, "stream": False},
        timeout=600,
    ).raise_for_status()
    print(f"[local] Model {LOCAL_MODEL!r} ready.")
