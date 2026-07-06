#!/usr/bin/env bash
# Do NOT use `set -e` here: a failed/slow ollama startup must not be fatal —
# agent.local_model.is_available() already degrades gracefully to remote-only.
set -uo pipefail

OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
OLLAMA_READY_TIMEOUT="${OLLAMA_READY_TIMEOUT:-20}"
OLLAMA_PID=""

cleanup() {
    if [ -n "${OLLAMA_PID}" ] && kill -0 "${OLLAMA_PID}" 2>/dev/null; then
        kill "${OLLAMA_PID}" 2>/dev/null
        wait "${OLLAMA_PID}" 2>/dev/null
    fi
}
trap cleanup EXIT INT TERM

echo "[entrypoint] starting ollama serve..." >&2
OLLAMA_HOST="${OLLAMA_HOST}" ollama serve >/tmp/ollama.log 2>&1 &
OLLAMA_PID=$!

ready=0
i=0
while [ "$i" -lt "${OLLAMA_READY_TIMEOUT}" ]; do
    if curl -sf "http://${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
        ready=1
        break
    fi
    i=$((i + 1))
    sleep 1
done

if [ "$ready" -eq 1 ]; then
    echo "[entrypoint] ollama ready after ${i}s" >&2
else
    echo "[entrypoint] WARNING: ollama not ready after ${OLLAMA_READY_TIMEOUT}s — continuing; agent will route to remote only" >&2
fi

python3 /app/batch_runner.py
status=$?
echo "[entrypoint] batch_runner.py exited ${status}" >&2
exit "$status"
