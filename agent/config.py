import os
from dotenv import load_dotenv

load_dotenv()

# --- Local model (via Ollama) ---
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "phi3:mini")
LOCAL_BASE_URL = os.getenv("LOCAL_BASE_URL", "http://localhost:11434")
LOCAL_TIMEOUT = int(os.getenv("LOCAL_TIMEOUT", "60"))

# --- Remote model (Fireworks AI) ---
FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY", "")
# Will be updated once models are revealed at kickoff
REMOTE_MODEL_FAST = os.getenv(
    "REMOTE_MODEL_FAST",
    "accounts/fireworks/models/llama-v3p1-8b-instruct",
)
REMOTE_MODEL_STRONG = os.getenv(
    "REMOTE_MODEL_STRONG",
    "accounts/fireworks/models/llama-v3p1-70b-instruct",
)
REMOTE_MAX_TOKENS = int(os.getenv("REMOTE_MAX_TOKENS", "1024"))

# --- Routing thresholds ---
# Complexity score 0–1; below LOW → local, above HIGH → remote, between → cascade
COMPLEXITY_LOW = float(os.getenv("COMPLEXITY_LOW", "0.30"))
COMPLEXITY_HIGH = float(os.getenv("COMPLEXITY_HIGH", "0.65"))

# Cascade: if local confidence is below this, escalate to remote
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.60"))

# If local inference takes longer than this (seconds), skip it in future for same task type
LOCAL_TIMEOUT_THRESHOLD = float(os.getenv("LOCAL_TIMEOUT_THRESHOLD", "45"))
