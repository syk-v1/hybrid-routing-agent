"""
Local evaluation script.
Run this before submitting to check accuracy vs token spend.

Usage:
    python eval/eval.py [--tasks eval/sample_tasks.json] [--verbose]
"""

import argparse
import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.agent import answer
from agent.remote_model import get_session_tokens, reset_session_tokens


# ---------------------------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------------------------

def _normalise(text: str) -> str:
    return text.lower().strip().rstrip(".").replace(",", "").replace("$", "")


def _check(result_text: str, task: dict) -> bool:
    """Return True if result satisfies the task's acceptance criteria."""
    norm = _normalise(result_text)

    # Exact / substring match on 'expected'
    if "expected" in task:
        exp = _normalise(str(task["expected"]))
        if exp in norm:
            return True

    # All substrings must appear for 'expected_contains'
    if "expected_contains" in task:
        return all(kw.lower() in result_text.lower() for kw in task["expected_contains"])

    return False


# ---------------------------------------------------------------------------
# Main eval loop
# ---------------------------------------------------------------------------

def run_eval(tasks_path: str, verbose: bool = False) -> None:
    with open(tasks_path) as f:
        tasks = json.load(f)

    reset_session_tokens()
    t_start = time.time()

    results = []
    correct = 0
    total_remote_tokens = 0

    print(f"\n{'='*60}")
    print(f" Evaluating {len(tasks)} tasks")
    print(f"{'='*60}\n")

    for task in tasks:
        tid = task["id"]
        query = task["query"]

        res = answer(query, verbose=verbose)

        passed = _check(res.answer, task)
        correct += int(passed)
        total_remote_tokens += res.remote_tokens

        status = "✓" if passed else "✗"
        token_note = f"  [{res.remote_tokens} remote tokens]" if res.remote_tokens else "  [local, 0 tokens]"
        route_note = f"route={res.route_taken}"

        print(f"  {status} [{tid}] {route_note}{token_note}")
        if verbose:
            print(f"     Q: {query[:80]}")
            print(f"     A: {res.answer[:120]}")
            if res.error:
                print(f"     ERROR: {res.error}")
            print()

        results.append({
            "id": tid,
            "passed": passed,
            "route": res.route_taken,
            "remote_tokens": res.remote_tokens,
            "answer_snippet": res.answer[:100],
        })

    elapsed = time.time() - t_start
    accuracy = correct / len(tasks) * 100
    session = get_session_tokens()

    print(f"\n{'='*60}")
    print(f" RESULTS")
    print(f"{'='*60}")
    print(f"  Accuracy          : {correct}/{len(tasks)} = {accuracy:.1f}%")
    print(f"  Remote tokens used: {session['total']} (prompt={session['prompt']}, completion={session['completion']})")
    print(f"  Total time        : {elapsed:.1f}s")
    print(f"{'='*60}\n")

    # Route breakdown
    route_counts: dict[str, int] = {}
    for r in results:
        route_counts[r["route"]] = route_counts.get(r["route"], 0) + 1
    print("  Route breakdown:")
    for route_label, count in sorted(route_counts.items()):
        print(f"    {route_label:<30} {count} task(s)")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the routing agent locally")
    parser.add_argument(
        "--tasks",
        default=os.path.join(os.path.dirname(__file__), "sample_tasks.json"),
        help="Path to tasks JSON file",
    )
    parser.add_argument("--verbose", action="store_true", help="Print answers and Q/A details")
    args = parser.parse_args()

    run_eval(args.tasks, verbose=args.verbose)
