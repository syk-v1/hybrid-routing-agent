"""
Dry-run test: patches local/remote with fakes so you can verify
the full agent pipeline without Ollama or a Fireworks API key.

Run: python dryrun_test.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ---- Patch local model: simulate Ollama unavailable ----
import agent.local_model as lm
from agent.local_model import LocalResult

lm.is_available = lambda: False
lm.run = lambda q: LocalResult(text="", confidence=0, latency=0, success=False, error="Ollama not running")

# ---- Patch remote model: return fake answers ----
import agent.remote_model as rm
from agent.remote_model import RemoteResult

def _fake_remote(query, *, use_strong_model=False, system=""):
    fake_answer = f"[REMOTE] answer for: {query[:50]}"
    tokens = len(query.split()) + 10
    rm._session_tokens["prompt"] += len(query.split())
    rm._session_tokens["completion"] += 10
    rm._session_tokens["total"] += tokens
    return RemoteResult(
        text=fake_answer,
        prompt_tokens=len(query.split()),
        completion_tokens=10,
        total_tokens=tokens,
        latency=0.1,
        model="fake-model",
        success=True,
    )

rm.run = _fake_remote

# ---- Now run the agent ----
from agent.agent import answer
from agent.remote_model import get_session_tokens

queries = [
    "12 + 47",
    "What is the capital of France?",
    "Write a Python function to implement quicksort",
    "What is the integral of x^2 dx?",
    "Explain the pros and cons of microservices vs monolith",
    "Translate hello to Spanish",
]

print("\n=== DRY RUN (local=unavailable, remote=faked) ===\n")

for q in queries:
    res = answer(q, verbose=True)
    print(f"  answer  : {res.answer}")
    print(f"  route   : {res.route_taken}")
    print(f"  tokens  : {res.remote_tokens}")
    print()

tok = get_session_tokens()
print(f"Total remote tokens this session: {tok['total']}")
print("=== DRY RUN COMPLETE ===\n")
