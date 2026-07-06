FROM python:3.11-slim

# --- system deps needed only to install Ollama and poll its HTTP API ---
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# --- install Ollama itself (network access at build time is fine — we control build+push) ---
# Prune GPU backend libs we don't need for CPU-only inference in the SAME layer as the
# install, since deleting files in a later layer does not shrink the image.
RUN curl -fsSL https://ollama.com/install.sh | sh \
    && (rm -rf /usr/lib/ollama/cuda_v* /usr/lib/ollama/rocm* 2>/dev/null || true)

# --- bake phi3:mini into the image at build time so no model download happens at eval runtime ---
# Each RUN is its own process tree, so start the server, wait for readiness, pull, then kill
# the server, all inside this one RUN so the pulled model files land in this same layer.
ENV OLLAMA_HOST=127.0.0.1:11434
RUN set -eux; \
    ollama serve & \
    SERVER_PID=$!; \
    tries=0; \
    until curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; do \
        tries=$((tries + 1)); \
        if [ "$tries" -ge 60 ]; then echo "ollama server failed to start" >&2; exit 1; fi; \
        sleep 1; \
    done; \
    ollama pull phi3:mini; \
    kill "$SERVER_PID"; \
    wait "$SERVER_PID" 2>/dev/null || true

WORKDIR /app

# --- python deps ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- app code (explicit COPY list so .env/eval/dev scripts never ship in the image) ---
COPY agent/ ./agent/
COPY batch_runner.py .
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
