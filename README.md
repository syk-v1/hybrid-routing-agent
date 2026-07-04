# hybrid-routing-agent

Routes each query to the cheapest model that can answer it correctly — local first, Fireworks AI as fallback. Built for the Fireworks AI Hackathon (Track 1).

## How it works

Every query gets a complexity score (0–1) based on signals like query length, whether it involves code, math, or multi-step reasoning. That score decides where it goes:

- **< 0.30** — local model only (phi3:mini via Ollama, costs nothing)
- **0.30–0.65** — try local first; if the model seems uncertain, escalate to remote
- **> 0.65** — straight to Fireworks AI

The local model runs for free. Remote calls are only made when necessary.

## Results

12/12 accuracy on the sample task suite with **0 remote tokens** used — phi3:mini handles everything in the test set on its own.

## Setup

```bash
git clone https://github.com/syk-v1/hybrid-routing-agent
cd hybrid-routing-agent
pip install -r requirements.txt
cp .env.example .env   # add your FIREWORKS_API_KEY
ollama pull phi3:mini
ollama serve
```

## Usage

```bash
# run a single query
python main.py "What is the capital of France?"

# evaluate accuracy and token spend across the test suite
python eval/eval.py --verbose

# try it without Ollama or an API key
python dryrun_test.py
```

## Configuration

Set these in `.env`:

| Variable | Default | What it does |
|---|---|---|
| `FIREWORKS_API_KEY` | — | Your Fireworks AI key |
| `LOCAL_MODEL` | `phi3:mini` | Local model name in Ollama |
| `REMOTE_MODEL_FAST` | `glm-5p1` | Remote model for most escalations |
| `REMOTE_MODEL_STRONG` | `gpt-oss-120b` | Remote model for very complex tasks |
| `COMPLEXITY_LOW` | `0.30` | Below this → always local |
| `COMPLEXITY_HIGH` | `0.65` | Above this → always remote |
| `CONFIDENCE_THRESHOLD` | `0.60` | Cascade: escalate if local confidence is below this |

## Project structure

```
agent/
  config.py       environment + thresholds
  router.py       complexity scorer (9 signals)
  local_model.py  Ollama wrapper + confidence heuristic
  remote_model.py Fireworks AI client + token counter
  agent.py        orchestrates routing and fallback
eval/
  eval.py         accuracy + token cost reporting
  sample_tasks.json
main.py           competition entry point
```

## Stack

- Local inference: [Ollama](https://ollama.com) + phi3:mini
- Remote inference: [Fireworks AI](https://fireworks.ai)
- Python 3.9+, no frameworks
