"""
Competition batch entry point (Docker container contract).

Reads /input/tasks.json ([{"task_id": "...", "prompt": "..."}, ...]),
answers every task via agent.agent.answer(), and writes /output/results.json
([{"task_id": "...", "answer": "..."}, ...]) — one entry per input task_id,
always valid JSON, always written before the process exits.
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeoutError
from threading import Semaphore

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.agent import answer
from agent.router import route as classify_route

INPUT_PATH = os.getenv("TASKS_INPUT_PATH", "/input/tasks.json")
OUTPUT_PATH = os.getenv("RESULTS_OUTPUT_PATH", "/output/results.json")
TOTAL_BUDGET_SECONDS = float(os.getenv("BATCH_TOTAL_BUDGET_SECONDS", "520"))
LOCAL_CONCURRENCY = max(1, int(os.getenv("LOCAL_CONCURRENCY", "2")))
REMOTE_CONCURRENCY = max(1, int(os.getenv("REMOTE_CONCURRENCY", "4")))

_local_gate = Semaphore(LOCAL_CONCURRENCY)
_remote_gate = Semaphore(REMOTE_CONCURRENCY)


def _process_task(task: dict, deadline: float) -> tuple[str, str, str]:
    task_id = str(task.get("task_id", ""))
    prompt = task.get("prompt", "")
    try:
        decision = classify_route(prompt)
        gate = _local_gate if decision.route in ("local", "cascade") else _remote_gate
        with gate:
            if time.monotonic() > deadline:
                return task_id, "", "skipped: past deadline"
            res = answer(prompt, verbose=False)
        return task_id, res.answer or "", res.error
    except Exception as exc:
        return task_id, "", f"{exc}\n{traceback.format_exc()}"


def main() -> int:
    start = time.monotonic()
    deadline = start + TOTAL_BUDGET_SECONDS

    try:
        with open(INPUT_PATH, "r", encoding="utf-8") as f:
            tasks = json.load(f)
        if not isinstance(tasks, list):
            raise ValueError("tasks.json must be a JSON array")
    except Exception as exc:
        sys.stderr.write(f"[batch_runner] FATAL: cannot read {INPUT_PATH}: {exc}\n")
        return 1

    task_ids = [str(t.get("task_id", f"unknown_{i}")) for i, t in enumerate(tasks)]
    results_by_id: dict[str, str] = {}

    executor = ThreadPoolExecutor(max_workers=LOCAL_CONCURRENCY + REMOTE_CONCURRENCY)
    futures = {}
    try:
        for i, task in enumerate(tasks):
            tid = str(task.get("task_id", f"unknown_{i}"))
            if time.monotonic() > deadline:
                results_by_id.setdefault(tid, "")
                continue
            futures[executor.submit(_process_task, task, deadline)] = tid

        remaining = max(0.001, deadline - time.monotonic())
        try:
            for fut in as_completed(futures, timeout=remaining):
                tid = futures[fut]
                try:
                    rid, ans, err = fut.result()
                    results_by_id[rid or tid] = ans
                    if err:
                        sys.stderr.write(f"[batch_runner] task {tid} error: {err}\n")
                except Exception as exc:
                    results_by_id[tid] = ""
                    sys.stderr.write(f"[batch_runner] task {tid} crashed: {exc}\n")
        except FutureTimeoutError:
            sys.stderr.write("[batch_runner] deadline reached; writing partial results\n")
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    output = [{"task_id": tid, "answer": results_by_id.get(tid, "")} for tid in task_ids]

    try:
        out_dir = os.path.dirname(OUTPUT_PATH) or "."
        os.makedirs(out_dir, exist_ok=True)
        tmp_path = OUTPUT_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, OUTPUT_PATH)
    except Exception as exc:
        sys.stderr.write(f"[batch_runner] FATAL: cannot write {OUTPUT_PATH}: {exc}\n")
        return 1

    sys.stderr.write(
        f"[batch_runner] wrote {len(output)} results in {time.monotonic() - start:.1f}s\n"
    )
    return 0


if __name__ == "__main__":
    rc = main()
    sys.stderr.flush()
    sys.stdout.flush()
    os._exit(rc)  # bypass ThreadPoolExecutor's atexit thread-join hang
