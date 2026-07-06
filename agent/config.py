import os
import re
from dotenv import load_dotenv

load_dotenv()

# --- Local model (via Ollama) ---
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "phi3:mini")
LOCAL_BASE_URL = os.getenv("LOCAL_BASE_URL", "http://localhost:11434")
LOCAL_TIMEOUT = int(os.getenv("LOCAL_TIMEOUT", "60"))

# --- Remote model (Fireworks AI) ---
FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY", "")
# Harness-injected at evaluation time; dev default points at the real Fireworks endpoint.
FIREWORKS_BASE_URL = os.getenv("FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1")
REMOTE_MAX_TOKENS = int(os.getenv("REMOTE_MAX_TOKENS", "1024"))
REMOTE_TIMEOUT = int(os.getenv("REMOTE_TIMEOUT", "45"))

# Harness-injected, comma-separated exact Fireworks model IDs allowed for this eval run.
ALLOWED_MODELS = [m.strip() for m in os.getenv("ALLOWED_MODELS", "").split(",") if m.strip()]


def _param_billion_count(model_id: str) -> float:
    """Best-effort parameter-count extraction, e.g. '...-70b' -> 70.0. -1 if unparseable."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*b\b", model_id, re.IGNORECASE)
    return float(m.group(1)) if m else -1.0


def _pick_fast_and_strong_models() -> tuple[str, str]:
    """
    Never hardcode a specific Fireworks model ID for submission — pick dynamically
    from ALLOWED_MODELS (published by the harness at eval time). Falls back to the
    REMOTE_MODEL_FAST / REMOTE_MODEL_STRONG env vars (local dev only) when
    ALLOWED_MODELS isn't set.
    """
    if ALLOWED_MODELS:
        if len(ALLOWED_MODELS) == 1:
            only = ALLOWED_MODELS[0]
            return only, only

        sized = [(mid, _param_billion_count(mid)) for mid in ALLOWED_MODELS]
        sized_known = [(mid, sz) for mid, sz in sized if sz >= 0]
        if len(sized_known) >= 2:
            sized_known.sort(key=lambda pair: pair[1])
            return sized_known[0][0], sized_known[-1][0]
        return ALLOWED_MODELS[0], ALLOWED_MODELS[-1]

    fast = os.getenv("REMOTE_MODEL_FAST", "accounts/fireworks/models/glm-5p1")
    strong = os.getenv("REMOTE_MODEL_STRONG", "accounts/fireworks/models/gpt-oss-120b")
    return fast, strong


REMOTE_MODEL_FAST, REMOTE_MODEL_STRONG = _pick_fast_and_strong_models()

# --- Routing thresholds ---
# Complexity score 0–1; below LOW → local, above HIGH → remote, between → cascade
COMPLEXITY_LOW = float(os.getenv("COMPLEXITY_LOW", "0.30"))
COMPLEXITY_HIGH = float(os.getenv("COMPLEXITY_HIGH", "0.65"))

# Cascade: if local confidence is below this, escalate to remote
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.60"))

# If local inference takes longer than this (seconds), skip it in future for same task type
LOCAL_TIMEOUT_THRESHOLD = float(os.getenv("LOCAL_TIMEOUT_THRESHOLD", "45"))
