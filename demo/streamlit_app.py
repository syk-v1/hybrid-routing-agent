"""
Live router demo for the Hybrid Routing Agent.

Type any prompt and watch the real 12-signal complexity router decide where it
would go — local (free), cascade (try local, maybe escalate), or remote
(Fireworks). This uses the exact agent/router.py from the submission and needs
no models, no API key, and no tokens: the routing decision is pure Python.

Deploy on Streamlit Community Cloud with main file path: demo/streamlit_app.py
"""
import os
import sys

# Make the repo root importable so we can use the real router.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from agent.router import route
from agent.config import COMPLEXITY_LOW, COMPLEXITY_HIGH

st.set_page_config(page_title="Hybrid Routing Agent — Live Router", page_icon="🧭", layout="centered")

ROUTE_META = {
    "local":   ("LOCAL",   "#34d399", "Handled by phi3:mini on-device — 0 scored tokens, free."),
    "cascade": ("CASCADE", "#fbbf24", "Try local first; escalate to Fireworks only if the answer looks shaky."),
    "remote":  ("REMOTE",  "#fb923c", "Sent straight to Fireworks AI — worth the tokens for this one."),
}

EXAMPLES = [
    "12 + 47",
    "What is the capital of France?",
    "Classify the sentiment of this review and justify: I loved this movie!",
    "Extract named entities as JSON: Barack Obama visited Paris in 2015.",
    "Summarise the following text in one sentence: ...",
    "Write a Python class implementing an LRU cache with O(1) get and put.",
    "Explain step by step the pros and cons of microservices vs a monolith.",
]

st.markdown(
    """
    <style>
      .stApp { background: linear-gradient(135deg,#0a0e1f 0%,#0f152e 55%,#1a1033 100%); }
      .block-container { max-width: 820px; }
      .sig { display:inline-block; padding:5px 12px; margin:4px 6px 4px 0; border-radius:14px;
             background:#171335; border:1px solid #8b5cf6; color:#c7d2fe;
             font-family:monospace; font-size:13px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🧭 Hybrid Routing Agent")
st.caption("Live complexity router · AMD Developer Hackathon Track 1 · no API key, no tokens — the routing itself is free")

st.write("**Try a prompt** and see how it gets triaged:")
cols = st.columns(3)
for i, ex in enumerate(EXAMPLES):
    if cols[i % 3].button(ex[:28] + ("…" if len(ex) > 28 else ""), key=f"ex{i}", use_container_width=True):
        st.session_state["query"] = ex

query = st.text_area("Your prompt", value=st.session_state.get("query", "12 + 47"), height=90)

if query.strip():
    decision = route(query)
    label, color, blurb = ROUTE_META[decision.route]

    st.markdown(
        f"<div style='font-size:2.1rem;font-weight:800;color:{color};margin-top:8px;'>→ {label}</div>"
        f"<div style='color:#cbd5e1;margin:2px 0 6px;'>{blurb}</div>",
        unsafe_allow_html=True,
    )

    st.markdown("**Complexity score**")
    st.progress(min(decision.complexity, 1.0))
    st.markdown(
        f"<div style='font-family:monospace;color:#94a3b8;'>"
        f"score = {decision.complexity:.2f} &nbsp;·&nbsp; "
        f"local ≤ {COMPLEXITY_LOW:.2f} &nbsp;·&nbsp; remote ≥ {COMPLEXITY_HIGH:.2f}</div>",
        unsafe_allow_html=True,
    )

    st.markdown("**Signals that fired**")
    signals = [s.strip() for s in decision.reason.split(",")] if decision.reason else []
    if signals and signals != ["no strong signals"]:
        st.markdown("".join(f"<span class='sig'>{s}</span>" for s in signals), unsafe_allow_html=True)
    else:
        st.markdown("<span class='sig'>no strong signals → default local</span>", unsafe_allow_html=True)

st.divider()
st.caption(
    "This is the real agent/router.py from the submission. In the full container, LOCAL runs on "
    "bundled phi3:mini (free) and REMOTE calls Fireworks AI — only the Fireworks tokens are scored. "
    "Image: ghcr.io/syk-v1/hybrid-routing-agent:latest"
)
