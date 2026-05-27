# ui/components/chat_panel.py
import streamlit as st


def render_chat_panel():
    risk = st.session_state.selected_risk
    if not risk:
        return

    st.subheader("Ask Follow‑ups")

    # Render chat history
    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    prompt = st.chat_input("Ask a question about this risk…")

    if prompt:
        st.session_state.chat.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # POC placeholder response
        reply = (
            "POC placeholder: I can answer this once we wire the agents. "
            "For now, key details are shown above (cause, customers, revenue, delay)."
        )
        st.session_state.chat.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.write(reply)
