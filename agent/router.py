"""
Multi-signal query complexity router.

Returns a float 0–1 (complexity score) and a routing decision:
  'local'   → handle with free local model
  'remote'  → send straight to Fireworks AI
  'cascade' → try local first, fall back to remote on low confidence
"""

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Signal keyword lists
# ---------------------------------------------------------------------------

_REASONING_KEYWORDS = [
    "step by step", "step-by-step", "explain why", "reason through",
    "analyze", "compare and contrast", "critique", "evaluate",
    "pros and cons", "trade-off", "tradeoff", "logical", "infer",
    "deduce", "argue", "justify", "prove", "disprove",
]

_CODE_KEYWORDS = [
    "write a function", "implement", "debug", "fix the bug", "refactor",
    "write code", "python script", "javascript", "typescript", "algorithm",
    "data structure", "leetcode", "write a program", "class that",
    "unit test", "write tests",
]

# Regex catches "write a Python function", "write a recursive function", etc.
_CODE_RE = re.compile(
    r"\b(write|implement|create|build|code)\b.{0,40}\b(function|class|method|algorithm|script|program|recursion|recursive)\b"
    r"|\b(debug|refactor|fix\s+\w*\s*bug|unit\s+test|write\s+tests?)\b",
    re.IGNORECASE,
)

_COMPLEX_MATH_KEYWORDS = [
    "integral", "derivative", "matrix", "eigenvalue", "differential",
    "probability distribution", "bayesian", "fourier", "laplace",
    "optimize", "calculus", "statistics", "regression", "variance",
]

_SIMPLE_MATH_PATTERN = re.compile(
    r"^[\d\s\+\-\*\/\(\)\.\^%=<>]+$"
)

_FACTUAL_PREFIXES = (
    "what is", "who is", "when was", "where is", "what are",
    "define ", "what does ", "how many ", "what year",
    "translate ", "convert ",
)

_UNCERTAINTY_MARKERS = [
    "i don't know", "i do not know", "i'm not sure", "i am not sure",
    "i cannot", "i can't", "unclear", "uncertain", "not enough information",
    "i'm unable", "i am unable",
]

_LONG_OUTPUT_KEYWORDS = [
    "write an essay", "write a report", "write a story", "write a blog",
    "summarize the following", "list all", "enumerate", "generate a list",
    "detailed explanation", "comprehensive",
]


# ---------------------------------------------------------------------------
# Dataclass for routing result
# ---------------------------------------------------------------------------

@dataclass
class RouteDecision:
    route: str          # 'local' | 'remote' | 'cascade'
    complexity: float   # 0–1
    reason: str         # human-readable explanation


# ---------------------------------------------------------------------------
# Complexity scorer
# ---------------------------------------------------------------------------

def _score(query: str) -> tuple[float, list[str]]:
    """Return (complexity 0–1, list of triggered signals)."""
    q = query.strip().lower()
    signals: list[str] = []
    score = 0.0

    # 1. Length signal (normalised to ~0.25 at 500 chars)
    length_score = min(len(q) / 2000, 0.25)
    if length_score > 0.05:
        signals.append(f"length({len(q)} chars)")
    score += length_score

    # 2. Simple arithmetic → strongly negative signal
    if _SIMPLE_MATH_PATTERN.match(q.replace(" ", "")):
        signals.append("simple_arithmetic")
        return max(0.0, score - 0.30), signals

    # 3. Factual / lookup → low complexity (only if no complex domain keywords)
    _has_complex = (
        any(kw in q for kw in _COMPLEX_MATH_KEYWORDS + _CODE_KEYWORDS)
        or bool(_CODE_RE.search(q))
    )
    if any(q.startswith(p) for p in _FACTUAL_PREFIXES) and len(q) < 120 and not _has_complex:
        signals.append("factual_lookup")
        score += 0.05
        return min(score, 0.25), signals

    # 4. Reasoning keywords
    for kw in _REASONING_KEYWORDS:
        if kw in q:
            signals.append(f"reasoning:{kw!r}")
            score += 0.30
            break

    # 4b. Generic explain/describe — weaker signal
    if re.search(r"\bexplain\b|\bdescribe\b|\bdiscuss\b", q) and "reasoning:" not in " ".join(signals):
        signals.append("explain_verb")
        score += 0.10

    # 5. Code generation (keyword list OR regex for natural-language phrasing)
    _code_hit = next((kw for kw in _CODE_KEYWORDS if kw in q), None) or (
        _CODE_RE.search(q) and "regex"
    )
    if _code_hit:
        signals.append(f"code:{_code_hit!r}")
        score += 0.35

    # 6. Complex math
    for kw in _COMPLEX_MATH_KEYWORDS:
        if kw in q:
            signals.append(f"complex_math:{kw!r}")
            score += 0.32
            break

    # 7. Long output expected
    for kw in _LONG_OUTPUT_KEYWORDS:
        if kw in q:
            signals.append(f"long_output:{kw!r}")
            score += 0.15
            break

    # 8. Word-problem math (costs/prices + comparisons)
    _word_problem = re.search(
        r"(\bcost|\bprice|\btotal|\bhow much|\bmore than|\btogether\b).{0,60}(\bhow much|\bcost|\bhow many|\bfind\b)",
        q,
        re.IGNORECASE,
    )
    if _word_problem:
        signals.append("word_problem")
        score += 0.22

    # 9. Multi-sentence / multi-step structure
    sentences = [s.strip() for s in re.split(r"[.!?]", q) if s.strip()]
    if len(sentences) >= 4:
        signals.append(f"multi_sentence({len(sentences)})")
        score += 0.10

    # 9. Question contains sub-questions
    sub_q = len(re.findall(r"\?", q))
    if sub_q >= 3:
        signals.append(f"multi_question({sub_q})")
        score += 0.10

    return min(score, 1.0), signals


# ---------------------------------------------------------------------------
# Public router
# ---------------------------------------------------------------------------

def route(query: str) -> RouteDecision:
    complexity, signals = _score(query)
    reason = ", ".join(signals) if signals else "no strong signals"

    from agent.config import COMPLEXITY_LOW, COMPLEXITY_HIGH

    if complexity <= COMPLEXITY_LOW:
        return RouteDecision("local", complexity, reason)
    if complexity >= COMPLEXITY_HIGH:
        return RouteDecision("remote", complexity, reason)
    return RouteDecision("cascade", complexity, reason)


# ---------------------------------------------------------------------------
# Output confidence checker (used after local inference)
# ---------------------------------------------------------------------------

def output_confidence(text: str) -> float:
    """
    Heuristic confidence in a local model output, 0–1.
    Used to decide whether to escalate to remote in cascade mode.
    """
    if not text or len(text.strip()) < 5:
        return 0.0

    t = text.lower()

    # Penalise explicit uncertainty (first hit is a heavy penalty)
    penalty = 0.50 if any(m in t for m in _UNCERTAINTY_MARKERS) else 0.0

    # Penalise very short answers to non-trivial queries
    length_score = min(len(text) / 100, 1.0) * 0.3

    # Reward well-structured output (has punctuation, paragraphs)
    structure_score = 0.0
    if "." in text or "\n" in text:
        structure_score += 0.2
    if len(text) > 50:
        structure_score += 0.2

    # Penalise repetition (quick heuristic)
    words = text.lower().split()
    if len(words) > 10:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.4:
            penalty += 0.20

    base = 0.5 + length_score + structure_score - penalty
    return max(0.0, min(1.0, base))
