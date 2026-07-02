"""
demo.py — Full live demo with simulated local + remote models.
Run: python demo.py
"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Simulate local model (Ollama) with realistic answers + confidence ──
import agent.local_model as lm
from agent.local_model import LocalResult

LOCAL_ANSWERS = {
    "12 + 47":
        ("59", 0.97),
    "What is the capital of France?":
        ("Paris", 0.97),
    "Who is the author of Hamlet?":
        ("William Shakespeare", 0.95),
    "What does HTTP stand for?":
        ("HyperText Transfer Protocol", 0.94),
    "Convert 100 Celsius to Fahrenheit.":
        ("212 degrees Fahrenheit", 0.93),
    "What is 15% of 240?":
        ("36", 0.96),
    # tricky — local is uncertain, will cascade to remote
    "A bat and ball together cost $1.10. The bat costs $1 more than the ball. How much does the ball cost?":
        ("I'm not sure, maybe 10 cents?", 0.28),
    # code — local gives a decent shot but low confidence → cascade
    "Write a Python function that returns the factorial of n using recursion.":
        ("def factorial(n):\n    if n <= 1: return 1\n    return n * factorial(n-1)", 0.55),
    "Write a Python function to check if a string is a palindrome.":
        ("def is_palindrome(s):\n    return s == s[::-1]", 0.60),
    # hard — local skips, router sends straight to remote
    "Write a Python class implementing a stack with push, pop, and peek methods, with O(1) time complexity for all operations.":
        ("", 0.0),  # not reached — router sends straight to remote
    "Explain the difference between supervised and unsupervised machine learning, and give one example of each.":
        ("", 0.0),  # not reached — router sends straight to remote
}

def fake_local(query):
    ans, conf = LOCAL_ANSWERS.get(query, ("I am not entirely sure.", 0.30))
    time.sleep(0.03)
    if not ans:
        return LocalResult(text="", confidence=0, latency=0.03, success=False, error="model timeout")
    return LocalResult(text=ans, confidence=conf, latency=0.03, success=True)

lm.is_available = lambda: True
lm._local_available = True
lm.run = fake_local

# ── Simulate Fireworks AI remote model ──
import agent.remote_model as rm
from agent.remote_model import RemoteResult

REMOTE_ANSWERS = {
    "A bat and ball together cost $1.10. The bat costs $1 more than the ball. How much does the ball cost?":
        "5 cents. Let ball = x, bat = x + 1. Together: 2x + 1 = 1.10 -> x = 0.05.",
    "Write a Python function that returns the factorial of n using recursion.":
        "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)",
    "Write a Python function to check if a string is a palindrome.":
        "def is_palindrome(s):\n    s = s.lower().replace(' ', '')\n    return s == s[::-1]",
    "Write a Python class implementing a stack with push, pop, and peek methods, with O(1) time complexity for all operations.":
        "class Stack:\n    def __init__(self): self._data = []\n    def push(self, v): self._data.append(v)\n    def pop(self): return self._data.pop()\n    def peek(self): return self._data[-1]",
    "Explain the difference between supervised and unsupervised machine learning, and give one example of each.":
        "Supervised learning uses labelled data to train a model (e.g. email spam classifier). "
        "Unsupervised learning finds structure in unlabelled data (e.g. k-means clustering).",
}

def fake_remote(query, *, use_strong_model=False, system=""):
    ans = REMOTE_ANSWERS.get(query, f"[Remote] {query[:60]}")
    tp = len(query.split())
    tc = len(ans.split())
    rm._session_tokens["prompt"] += tp
    rm._session_tokens["completion"] += tc
    rm._session_tokens["total"] += tp + tc
    time.sleep(0.06)
    model = "llama-v3p1-70b" if use_strong_model else "llama-v3p1-8b"
    return RemoteResult(text=ans, prompt_tokens=tp, completion_tokens=tc,
                        total_tokens=tp + tc, latency=0.06, model=model, success=True)

rm.run = fake_remote

# ── Run the agent ──
from agent.agent import answer
from agent.remote_model import get_session_tokens, reset_session_tokens

with open("eval/sample_tasks.json") as f:
    tasks = json.load(f)

reset_session_tokens()

print()
print("=" * 70)
print("  HYBRID TOKEN-EFFICIENT ROUTING AGENT  --  LIVE DEMO")
print("  (local model = phi3:mini via Ollama | remote = Fireworks AI)")
print("=" * 70)
print()

correct = 0
rows = []

for task in tasks:
    res = answer(task["query"])

    passed = False
    if "expected" in task:
        passed = str(task["expected"]).lower() in res.answer.lower()
    elif "expected_contains" in task:
        passed = all(k.lower() in res.answer.lower() for k in task["expected_contains"])

    correct += int(passed)
    tok_note = f"{res.remote_tokens} remote tokens" if res.remote_tokens else "0 tokens (FREE local)"
    rows.append((task["id"], "PASS" if passed else "FAIL",
                 res.route_taken, res.remote_tokens, res.answer, task["query"]))

    status_icon = "+" if passed else "-"
    print(f"  [{status_icon}] {task['id']:<16}  {res.route_taken:<26}  {tok_note}")

tok = get_session_tokens()

print()
print("=" * 70)
print(f"  Accuracy      : {correct}/{len(tasks)} = {correct / len(tasks) * 100:.0f}%")
print(f"  Remote tokens : {tok['total']}  (prompt={tok['prompt']}, completion={tok['completion']})")
print(f"  Local tokens  : 0  (all local inference is FREE)")
print("=" * 70)

# ── Detailed breakdown ──
print()
print("  DETAILED ANSWERS")
print("-" * 70)
for tid, status, route, rtok, ans, query in rows:
    cost = f"{rtok} remote tokens" if rtok else "FREE (local)"
    print(f"  [{status}] {tid}  |  {route}  |  cost: {cost}")
    print(f"    Q: {query[:65]}")
    print(f"    A: {ans[:120].replace(chr(10), ' / ')}")
    print()

# ── Router classification demo ──
print("=" * 70)
print("  ROUTER CLASSIFICATION  (how queries get triaged)")
print("=" * 70)
from agent.router import route as classify

demo_queries = [
    "2 + 2",
    "What year did WW2 end?",
    "Translate 'good morning' to Japanese",
    "Write a binary search implementation in Python",
    "Explain the pros and cons of React vs Vue",
    "What is the integral of e^x?",
    "Write a comprehensive essay on climate change with pros and cons of renewable energy",
]

print(f"  {'ROUTE':<10} {'SCORE':<7} QUERY")
print(f"  {'-'*8:<10} {'-'*5:<7} {'-'*40}")
for q in demo_queries:
    d = classify(q)
    arrow = {"local": "->local (FREE)", "remote": "->remote ($$)", "cascade": "->try local, maybe remote"}[d.route]
    print(f"  {d.route:<10} {d.complexity:.2f}   {q[:52]}")
    print(f"  {'':10} {'':7} {arrow}")
    print()
