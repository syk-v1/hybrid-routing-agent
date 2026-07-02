# setup.ps1 — Windows PowerShell setup script
# Run once: .\setup.ps1

Write-Host "`n=== Hybrid Routing Agent Setup ===" -ForegroundColor Cyan

# 1. Python venv
if (-not (Test-Path ".venv")) {
    Write-Host "`n[1/4] Creating virtual environment..."
    python -m venv .venv
}
& .\.venv\Scripts\Activate.ps1

# 2. Install Python deps
Write-Host "`n[2/4] Installing Python dependencies..."
pip install -r requirements.txt --quiet

# 3. Copy .env if needed
if (-not (Test-Path ".env")) {
    Write-Host "`n[3/4] Creating .env from .env.example..."
    Copy-Item .env.example .env
    Write-Host "  -> Edit .env and set FIREWORKS_API_KEY" -ForegroundColor Yellow
} else {
    Write-Host "`n[3/4] .env already exists — skipping"
}

# 4. Ollama check
Write-Host "`n[4/4] Checking Ollama..."
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollama) {
    Write-Host "  Ollama found at $($ollama.Source)"
    Write-Host "  Pulling phi3:mini (this may take a while on first run)..."
    ollama pull phi3:mini
} else {
    Write-Host "  Ollama not found. Install from https://ollama.com then run:" -ForegroundColor Yellow
    Write-Host "    ollama pull phi3:mini" -ForegroundColor Yellow
}

Write-Host "`n=== Setup complete ===" -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  1. Edit .env — set FIREWORKS_API_KEY"
Write-Host "  2. ollama serve   (in a separate terminal)"
Write-Host "  3. python eval/eval.py --verbose"
Write-Host "  4. python main.py `"What is the capital of France?`""
