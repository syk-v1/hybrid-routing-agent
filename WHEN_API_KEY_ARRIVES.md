# When Your Fireworks API Key Arrives

Your Fireworks AI account is provisioned but the API key isn't ready yet.
Once you get it, do the following:

## Step 1 — Add the key to .env

Open `C:\Users\ndu20\hybrid-routing-agent\.env` and replace the empty value:

```env
FIREWORKS_API_KEY=fw_your_actual_key_here
```

## Step 2 — Re-run the eval with remote enabled

```powershell
$env:PATH = $env:PATH + ";C:\Users\ndu20\AppData\Local\Programs\Ollama"
$env:PYTHONUTF8 = "1"
cd C:\Users\ndu20\hybrid-routing-agent
python eval/eval.py --verbose
```

This will show you which tasks now hit Fireworks vs stay local.

## Step 3 — Test a single hard query end to end

```powershell
python main.py "Explain the pros and cons of microservices vs monolithic architecture"
```

Check stderr — it should show `route=cascade->remote` and a non-zero `remote_tokens` count,
confirming the full local → remote fallback pipeline is working.

## Step 4 — Commit the (empty) .env change note (NOT the key itself)

The `.env` file is in `.gitignore` so your key can never be accidentally pushed.
Nothing to commit — just verify with:

```powershell
git status
```

`.env` should show as untracked (ignored), not staged.

## What's already working (no key needed)

- Ollama + phi3:mini installed and running
- 12/12 accuracy on sample tasks with 0 remote tokens
- Full routing pipeline: local → cascade → remote
- GitHub repo live at https://github.com/syk-v1/hybrid-routing-agent

## Notes

- Fireworks API key starts with `fw_`
- Find it at: fireworks.ai → profile → API Keys → Create API Key
- The agent uses the 8B model for normal tasks and 70B for very complex ones (complexity > 0.85)
- Remote model names will be updated on hackathon kickoff day when official models are revealed
