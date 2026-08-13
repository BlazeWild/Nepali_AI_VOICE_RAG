import time
import streamlit as st
from dotenv import load_dotenv
from speech import transcribe_speech, text_to_speech
from rag import query_rag_llm

load_dotenv()

st.set_page_config(page_title="Voice RAG Agent", page_icon="🎙️", layout="wide")

st.markdown("""
<style>
.stAudioInput {
    position: fixed;
    bottom: 0;
    width: 100%;
    z-index: 999;
    background-color: var(--background-color);
    padding-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

# session state setup
if "call_status" not in st.session_state:
    st.session_state.call_status = "disconnected"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "audio_key" not in st.session_state:
    st.session_state.audio_key = 0

st.title("📞 Voice RAG Agent")

if st.session_state.call_status == "disconnected":
    st.markdown("### Enter phone number to call the AI Agent")
    st.text_input("Phone Number:", value="+977-9800000000")
    if st.button("Call", type="primary", use_container_width=True):
        st.session_state.call_status = "connecting"
        st.rerun()

elif st.session_state.call_status == "connecting":
    with st.spinner("Connecting to Agent..."):
        time.sleep(2)
    greeting = "नमस्कार! म तपाईंलाई कसरी सहयोग गर्न सक्छु?"
    st.session_state.messages = [
        {"role": "assistant", "content": greeting, "audio": text_to_speech(greeting)}
    ]
    st.session_state.call_status = "connected"
    st.rerun()

elif st.session_state.call_status == "connected":
    col1, col2 = st.columns([4, 1])
    with col1:
        st.success("🟢 Connected to AI Agent")
    with col2:
        if st.button("End Call", type="primary", use_container_width=True):
            st.session_state.call_status = "disconnected"
            st.session_state.messages = []
            st.rerun()

    st.divider()

    # render chat history
    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("audio"):
                # autoplay only the latest assistant message
                autoplay = idx == len(st.session_state.messages) - 1 and msg["role"] == "assistant"
                st.audio(msg["audio"], format="audio/mp3", autoplay=autoplay)

    recorded = st.audio_input("Speak to AI Agent:", key=f"audio_input_{st.session_state.audio_key}")

    if recorded:
        audio_bytes = recorded.read()

        with st.spinner("Transcribing..."):
            user_text = transcribe_speech(audio_bytes, language="ne")

        if user_text:
            st.session_state.messages.append({"role": "user", "content": user_text})

            with st.spinner("Thinking..."):
                result = query_rag_llm(user_text)
                answer = result["answer"]

            with st.spinner("Speaking..."):
                audio_path = text_to_speech(answer)

            st.session_state.messages.append({"role": "assistant", "content": answer, "audio": audio_path})
            st.session_state.audio_key += 1
            st.rerun()
