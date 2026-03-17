"""
Streamlit UI for ContextShop.

Run: streamlit run app.py
"""

import streamlit as st

from src.agent import AgentState, run_turn
from src.ingest import get_client

st.set_page_config(page_title="ContextShop", page_icon="🛒", layout="wide")

st.title("🛒 ContextShop")
st.caption("A retail agent that gets smarter with every message — powered by Qdrant context engineering")

# ── Init session state ──────────────────────────────────────────────────────
if "agent_state" not in st.session_state:
    st.session_state.agent_state = AgentState()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "qdrant" not in st.session_state:
    st.session_state.qdrant = get_client()

col_chat, col_metrics = st.columns([2, 1])

# ── Chat column ──────────────────────────────────────────────────────────────
with col_chat:
    st.subheader("Chat")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    query = st.chat_input("Ask about sports & outdoor products...")

    if query:
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.write(query)

        with st.spinner("Thinking..."):
            answer, new_state = run_turn(
                query,
                st.session_state.agent_state,
                st.session_state.qdrant,
                verbose=False,
            )
            st.session_state.agent_state = new_state

        st.session_state.messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.write(answer)

        st.rerun()

# ── Metrics column ───────────────────────────────────────────────────────────
with col_metrics:
    st.subheader("Context Engine Live")

    turns = st.session_state.agent_state.tracker.turns
    turn_num = st.session_state.agent_state.turn_num

    st.metric("Conversation turns", turn_num)

    if turns:
        latest = turns[-1]
        st.metric("Retrieval score (latest)", f"{latest.avg_product_score:.3f}")
        st.metric("Context tokens used", latest.total_tokens)

        st.markdown("**Memory status**")
        st.write(f"- Episodic summaries: {latest.episodic_chunks}")
        st.write(f"- Preference facts: {latest.preference_chunks}")
        st.write(f"- Facts extracted this turn: {latest.facts_extracted}")

        if len(turns) >= 2:
            st.markdown("---")
            st.markdown("**Score progression**")
            scores = [t.avg_product_score for t in turns]
            st.line_chart({"Retrieval score": scores})

            cold = turns[0]
            warm = turns[-1]
            delta = warm.avg_product_score - cold.avg_product_score
            st.metric(
                "Score improvement (turn 0 → now)",
                f"{warm.avg_product_score:.3f}",
                delta=f"{delta:+.3f}",
            )
    else:
        st.info("Start chatting to see context metrics.")

    st.markdown("---")
    st.caption(f"Session: `{st.session_state.agent_state.session_id[:8]}`")
    if st.button("Reset session"):
        st.session_state.agent_state = AgentState()  # new session_id generated automatically
        st.session_state.messages = []
        st.rerun()
