"""
Streamlit demo UI for Mumz Assistant.
Run: streamlit run app/streamlit_app.py
"""

import streamlit as st
from app.agent import MumzAgent

st.set_page_config(page_title="Mumz Assistant", page_icon="👶", layout="wide")

st.title("👶 Mumz Assistant")
st.caption("Bilingual (EN/AR) AI shopping concierge for Mumzworld")

@st.cache_resource
def load_agent() -> MumzAgent:
    return MumzAgent()

agent = load_agent()

with st.sidebar:
    st.header("About")
    st.markdown(
        "RAG over **50 baby products** + **20 parenting guidelines** "
        "(WHO / AAP / CDC sourced).\n\n"
        "**Stack:** multilingual MiniLM embeddings → FAISS → Gemini 2.0 Flash → "
        "safety guardrails."
    )
    st.markdown("---")
    st.subheader("Try these:")
    examples = [
        "Is Aptamil Stage 1 halal?",
        "هل حليب أبتاميل حلال؟",
        "Best car seat for a newborn?",
        "When can I introduce solid food?",
        "متى يمكنني إدخال الطعام الصلب؟",
        "Diaper rash treatment for 6 month old",
    ]
    for ex in examples:
        if st.button(ex, key=ex, use_container_width=True):
            st.session_state["pending"] = ex

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("citations"):
            with st.expander("Citations & retrieval"):
                st.json(m["citations"])

prompt = st.chat_input("Ask anything about products or parenting (EN or AR)…")
if "pending" in st.session_state:
    prompt = st.session_state.pop("pending")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            r = agent.answer(prompt)
        st.markdown(r.answer)
        if r.safety_flags:
            st.warning(f"Safety flags: {', '.join(r.safety_flags)}")
        with st.expander("Citations & retrieval"):
            st.json({"citations": r.citations, "language": r.language})
        st.session_state.messages.append({
            "role": "assistant",
            "content": r.answer,
            "citations": {"citations": r.citations, "language": r.language},
        })
