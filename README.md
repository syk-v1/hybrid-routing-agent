# Hybrid Token-Efficient Routing Agent

> An intelligent AI agent that completes tasks at minimum token cost by routing each query to the cheapest model capable of solving it — local inference first, remote AI as a fallback.

Built for **Track 1 of the Fireworks AI Hackathon** — scored on token efficiency and output accuracy.

---

## How It Works

Every query goes through a three-stage pipeline:

```
Query
  │
  ▼
┌─────────────────────────────────────────┐
│           COMPLEXITY ROUTER             │
│  Scores query 0–1 across 9 signals:     │
│  length · code · math · reasoning ·     │
│  word-problems · multi-step · explain   │
└──────────┬──────────────────┬───────────┘
           │                  │
     score < 0.30       score > 0.65
           │                  │
           ▼                  ▼
    ┌─────────────┐    ┌──────────────┐
    │ LOCAL MODEL │    │  REMOTE API  │
    │ phi3:mini   │    │ Fireworks AI │
    │ via Ollama  │    │ llama-3.1-8b │
    │  FREE ✓     │    │  paid $$     │
    └──────┬──────┘    └──────────────┘
           │
     0.30–0.65 → CASCADE MODE
           │
           ▼
    ┌─────────────┐
    │ LOCAL first │──conf ≥ 0.60──→ return local answer (FREE)
    │             │
    │             │──conf < 0.60──→ escalate to remote
    └─────────────┘
```

**Key insight:** Local tokens cost zero. The router's job is to keep as many queries as possible on the local model without sacrificing accuracy.

---

## Results

Tested against 12 tasks spanning math, factual Q&A, code generation, and reasoning:

| Metric | Score |
|---|---|
| Accuracy | **12 / 12 (100%)** |
| Remote tokens used | **0** |
| Local tokens used | **0 (always free)** |
| Route breakdown | 8 local · 4 cascade→local |

All tasks solved locally by `phi3:mini` with zero remote API calls.

---

## Architecture

```
hybrid-routing-agent/
├── agent/
│   ├── config.py        # All thresholds and model names (via .env)
│   ├── router.py        # Multi-signal complexity scorer
│   ├── local_model.py   # Ollama wrapper + output confidence heuristic
│   ├── remote_model.py  # Fireworks AI client + session token counter
│   └── agent.py         # Orchestrator: routes, runs, falls back
├── eval/
│   ├── eval.py          # Accuracy + token-cost scoring
│   └── sample_tasks.json
├── main.py              # Competition entry point
├── demo.py              # Full demo with simulated models
└── dryrun_test.py       # Pipeline test without Ollama or API key
```

### Router signals

The router scores each query across 9 independent signals:

| Signal | Score added | Example trigger |
|---|---|---|
| Query length | up to +0.25 | long multi-paragraph prompts |
| Simple arithmetic | −0.30 | `12 + 47`, `15% of 240` |
| Factual lookup | capped at 0.25 | `What is the capital of France?` |
| Reasoning keywords | +0.30 | `pros and cons`, `step by step` |
| Code generation (regex) | +0.35 | `Write a Python function that...` |
| Complex math | +0.32 | `integral`, `derivative`, `matrix` |
| Long output expected | +0.15 | `write an essay`, `summarize` |
| Word-problem math | +0.22 | price + comparison + "how much" |
| Multi-sentence structure | +0.10 | 4+ sentences in the query |

### Routing thresholds (tunable via `.env`)

| Range | Decision |
|---|---|
| score < 0.30 | Always local — no API call |
| 0.30 – 0.65 | Cascade — try local, escalate if confidence < 0.60 |
| score > 0.65 | Always remote |

### Confidence heuristic

After local inference, the agent estimates output confidence (0–1):
- Penalises uncertainty markers ("I'm not sure", "I cannot")
- Rewards structured output (paragraphs, punctuation)
- Penalises repetition (low unique-word ratio)
- Outputs below the threshold are escalated to remote

---

## Quickstart

### Prerequisites

- Python 3.9+
- [Ollama](https://ollama.com) (for local inference)
- Fireworks AI API key (for remote fallback)

### Setup

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/hybrid-routing-agent
cd hybrid-routing-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env and set FIREWORKS_API_KEY=fw_...

# 4. Pull local model
ollama pull phi3:mini

# 5. Start Ollama
ollama serve
```

### Run

```bash
# Single query (competition entry point)
python main.py "What is the capital of France?"
python main.py "Write a Python function that returns the factorial of n"

# Evaluate accuracy + token cost across test suite
python eval/eval.py --verbose

# Full demo with simulated models (no Ollama or API key needed)
python demo.py

# Pipeline test without any external dependencies
python dryrun_test.py
```

### Example output

```
$ python main.py "12 + 47"
59
[route=local complexity=0.00 remote_tokens=0 conf=1.00]

$ python main.py "Write a Python function to check if a string is a palindrome"
def is_palindrome(s: str) -> bool:
    return s == s[::-1]
[route=cascade->local complexity=0.38 remote_tokens=0 conf=1.00]

$ python main.py "What is the integral of e^x?"
The integral of e^x is e^x + C, where C is the constant of integration.
[route=cascade->remote complexity=0.34 remote_tokens=31 conf=0.42]
```

---

## Configuration

All tunable via `.env`:

```env
# Fireworks AI
FIREWORKS_API_KEY=fw_...

# Models
LOCAL_MODEL=phi3:mini
REMOTE_MODEL_FAST=accounts/fireworks/models/llama-v3p1-8b-instruct
REMOTE_MODEL_STRONG=accounts/fireworks/models/llama-v3p1-70b-instruct

# Routing thresholds
COMPLEXITY_LOW=0.30       # below → always local
COMPLEXITY_HIGH=0.65      # above → always remote
CONFIDENCE_THRESHOLD=0.60 # cascade: escalate if local confidence is below this

# Limits
LOCAL_TIMEOUT=120
REMOTE_MAX_TOKENS=1024
```

---

## Tuning for competition tasks

After kickoff tasks are revealed:

1. Add them to `eval/sample_tasks.json`
2. Run `python eval/eval.py --verbose` to see accuracy and token spend
3. Lower `COMPLEXITY_LOW` → more queries go local (saves tokens, risks accuracy)
4. Raise `CONFIDENCE_THRESHOLD` → more cascade queries escalate to remote (costs tokens, gains accuracy)
5. Swap `LOCAL_MODEL` for a larger local model if hardware allows

---

## Tech stack

| Component | Technology |
|---|---|
| Local inference | [Ollama](https://ollama.com) + phi3:mini |
| Remote inference | [Fireworks AI](https://fireworks.ai) API |
| Router | Rule-based multi-signal scorer + regex |
| Language | Python 3.9+ |
| Dependencies | `fireworks-ai`, `requests`, `python-dotenv` |

---

## Hackathon

Built for **Fireworks AI Hackathon — Track 1: Hybrid Token-Efficient Routing Agent**

> Build an AI agent that gets the job done using the least tokens possible. The agent must complete tasks autonomously by deciding in real time whether to use a local model or call a remote model via Fireworks AI. Goal: pick the cheapest option every time, without falling below the accuracy threshold.

Scoring: **token count × accuracy** — this agent optimises both simultaneously by routing intelligently rather than always calling the expensive remote model.
