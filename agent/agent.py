"""
Main orchestrator: routes each query, runs local or remote inference,
returns the answer and logs what happened.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from agent.config import CONFIDENCE_THRESHOLD
from agent.router import route, RouteDecision
from agent import local_model, remote_model


@dataclass
class AgentResult:
    answer: str
    route_taken: str            # 'local' | 'remote' | 'cascade->local' | 'cascade->remote'
    complexity: float
    router_reason: str
    remote_tokens: int = 0
    local_latency: float = 0.0
    remote_latency: float = 0.0
    confidence: float = 0.0
    error: str = ""

    @property
    def total_latency(self) -> float:
        return self.local_latency + self.remote_latency


_local_available: bool | None = None  # cached after first check


def _ensure_local() -> bool:
    global _local_available
    if _local_available is None:
        _local_available = local_model.is_available()
    return _local_available


def answer(query: str, verbose: bool = False) -> AgentResult:
    """
    Route a query and return an AgentResult.

    verbose=True prints a one-line log to stdout.
    """
    decision: RouteDecision = route(query)

    def _log(msg: str) -> None:
        if verbose:
            print(f"[agent] {msg}")

    _log(f"complexity={decision.complexity:.2f} route={decision.route!r} ({decision.reason})")

    # ------------------------------------------------------------------ local
    if decision.route == "local":
        if not _ensure_local():
            _log("local unavailable -> falling back to remote")
            return _run_remote(query, decision, "local->remote(unavailable)")

        res = local_model.run(query)
        if res.success:
            _log(f"local ✓ conf={res.confidence:.2f} lat={res.latency:.1f}s")
            return AgentResult(
                answer=res.text,
                route_taken="local",
                complexity=decision.complexity,
                router_reason=decision.reason,
                local_latency=res.latency,
                confidence=res.confidence,
            )
        _log(f"local failed ({res.error}) -> remote")
        return _run_remote(query, decision, "local->remote(error)")

    # ----------------------------------------------------------------- remote
    if decision.route == "remote":
        result = _run_remote(query, decision, "remote")
        if result.error and _ensure_local():
            # A local attempt is free and beats an empty answer if remote is down.
            _log(f"remote failed ({result.error}) -> trying local as last resort")
            res = local_model.run(query)
            if res.success and res.text:
                return AgentResult(
                    answer=res.text,
                    route_taken="remote->local(fallback)",
                    complexity=decision.complexity,
                    router_reason=decision.reason,
                    local_latency=res.latency,
                    remote_latency=result.remote_latency,
                    confidence=res.confidence,
                )
        return result

    # ---------------------------------------------------------------- cascade
    if not _ensure_local():
        _log("local unavailable -> remote")
        return _run_remote(query, decision, "cascade->remote(unavailable)")

    local_res = local_model.run(query)
    if not local_res.success:
        _log(f"local failed ({local_res.error}) -> remote")
        return _run_remote(query, decision, "cascade->remote(local_error)")

    _log(f"local conf={local_res.confidence:.2f} (threshold={CONFIDENCE_THRESHOLD})")

    if local_res.confidence >= CONFIDENCE_THRESHOLD:
        _log("cascade -> keeping local answer")
        return AgentResult(
            answer=local_res.text,
            route_taken="cascade->local",
            complexity=decision.complexity,
            router_reason=decision.reason,
            local_latency=local_res.latency,
            confidence=local_res.confidence,
        )

    _log("cascade -> escalating to remote")
    result = _run_remote(query, decision, "cascade->remote")
    result.local_latency = local_res.latency
    if result.error and local_res.text:
        # Remote failed — the low-confidence local answer still beats an empty one.
        _log(f"remote failed ({result.error}) -> keeping local answer as fallback")
        return AgentResult(
            answer=local_res.text,
            route_taken="cascade->local(remote_failed)",
            complexity=decision.complexity,
            router_reason=decision.reason,
            local_latency=local_res.latency,
            remote_latency=result.remote_latency,
            confidence=local_res.confidence,
        )
    return result


def _run_remote(query: str, decision: RouteDecision, route_label: str) -> AgentResult:
    use_strong = decision.complexity >= 0.85
    rr = remote_model.run(query, use_strong_model=use_strong)

    if rr.success:
        return AgentResult(
            answer=rr.text,
            route_taken=route_label,
            complexity=decision.complexity,
            router_reason=decision.reason,
            remote_tokens=rr.total_tokens,
            remote_latency=rr.latency,
        )
    return AgentResult(
        answer="",
        route_taken=route_label,
        complexity=decision.complexity,
        router_reason=decision.reason,
        remote_tokens=0,
        remote_latency=rr.latency,
        error=rr.error,
    )
