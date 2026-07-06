"""
Manual single-query dev/debug tool. NOT the competition entry point —
the Docker submission runs batch_runner.py via docker-entrypoint.sh, which
reads /input/tasks.json and writes /output/results.json.

Use this script for quick local testing of a single query:
    python main.py "<query>"

It prints ONLY the answer to stdout (no extra text).
Token counts are logged to stderr so they don't pollute stdout.

Example:
    python main.py "What is 12 + 47?"
    → 59
"""

import sys
import os

# Make sure the project root is on the path regardless of cwd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.agent import answer
from agent.remote_model import get_session_tokens


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python main.py \"<query>\"", file=sys.stderr)
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    result = answer(query, verbose=False)

    if result.error:
        print(f"[ERROR] {result.error}", file=sys.stderr)
        sys.exit(1)

    # Only the answer goes to stdout — judges read this
    print(result.answer)

    # Diagnostics to stderr (not scored)
    tokens = get_session_tokens()
    print(
        f"[route={result.route_taken} complexity={result.complexity:.2f} "
        f"remote_tokens={result.remote_tokens} conf={result.confidence:.2f}]",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
