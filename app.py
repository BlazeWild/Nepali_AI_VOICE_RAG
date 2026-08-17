import os
import sys
import time
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from speech import transcribe_speech, text_to_speech
from rag import query_rag_llm, preload_all_models

st.set_page_config(
    page_title="Nepali Voice RAG Agent (Gemma 4 + Qwen3-ASR)",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom Styling matching liveapp.py aesthetic
st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }
.stApp {
    background: radial-gradient(circle at 50% 45%, #1e1b4b 0%, #0f172a 55%, #030712 100%) !important;
    color: #f8fafc;
}
.orb-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 20px 0;
}
.orb-element {
    width: 140px;
    height: 140px;
    border-radius: 50%;
    background: linear-gradient(135deg,#10b981,#047857);
    border: 3px solid #34d399;
    box-shadow: 0 0 50px rgba(16,185,129,0.6);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    animation: glowPulse 2.2s infinite;
}
.orb-icon { font-size: 36px; margin-bottom: 4px; }
.orb-label { font-size: 12px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: #fff; }

@keyframes glowPulse {
    0%,100% { box-shadow: 0 0 30px rgba(16,185,129,0.45); }
    50% { box-shadow: 0 0 65px rgba(16,185,129,0.85); }
}

.status-pill {
    display: inline-block;
    padding: 6px 20px;
    border-radius: 999px;
    font-size: 14px;
    font-weight: 600;
    background: rgba(30,41,59,0.8);
    border: 1px solid rgba(16,185,129,0.5);
    color: #34d399;
    box-shadow: 0 0 14px rgba(16,185,129,0.4);
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)

# Session state setup
if "call_status" not in st.session_state:
    st.session_state.call_status = "disconnected"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "audio_key" not in st.session_state:
    st.session_state.audio_key = 0

# Ringing audio component
RING_AUDIO_HTML = """
<script>
(function() {
    try {
        const ringCtx = new (window.AudioContext || window.webkitAudioContext)();
        for (let burst = 0; burst < 2; burst++) {
            const t = ringCtx.currentTime + burst * 0.6;
            const oscA = ringCtx.createOscillator();
            const gainA = ringCtx.createGain();
            oscA.type = 'sine'; oscA.frequency.setValueAtTime(440, t);
            gainA.gain.setValueAtTime(0, t);
            gainA.gain.linearRampToValueAtTime(0.25, t + 0.02);
            gainA.gain.setValueAtTime(0.25, t + 0.38);
            gainA.gain.linearRampToValueAtTime(0, t + 0.4);
            oscA.connect(gainA); gainA.connect(ringCtx.destination);
            oscA.start(t); oscA.stop(t + 0.4);
        }
    } catch(e) {}
})();
</script>
"""

st.markdown("<h1 style='text-align: center; margin-top: 10px;'>🎙️ Nepali Voice RAG Agent</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94a3b8;'>Gemma 4 Open-Source LLM + Qwen3-ASR (8-Bit GPU)</p>", unsafe_allow_html=True)

if st.session_state.call_status == "disconnected":
    st.markdown("""
    <div class="orb-container">
        <div class="status-pill" style="color: #94a3b8; border-color: #334155;">Click Start Call to Begin</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("📞 Start Call", type="primary", use_container_width=True):
            st.session_state.call_status = "connecting"
            st.rerun()

elif st.session_state.call_status == "connecting":
    # 0.2s Ring sound synthesizer
    st.components.v1.html(RING_AUDIO_HTML, height=0)

    with st.spinner("Pre-loading Qwen3-ASR 8-Bit Model & Connecting to Agent..."):
        preload_all_models()
        greeting = "नमस्कार! म तपाईंलाई के सहयोग गर्न सक्छु होला?"
        greeting_audio = text_to_speech(greeting)
        st.session_state.messages = [
            {"role": "assistant", "content": greeting, "audio": greeting_audio}
        ]
    st.session_state.call_status = "connected"
    st.rerun()

elif st.session_state.call_status == "connected":
    col_a, col_b, col_c = st.columns([1, 3, 1])
    with col_b:
        st.markdown("""
        <div class="orb-container">
            <div class="status-pill">🟢 Connected — AI Voice Agent Active</div>
            <div class="orb-element">
                <div class="orb-icon">📞</div>
                <div class="orb-label">Connected</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_c:
        if st.button("❌ End Call", type="primary", use_container_width=True):
            st.session_state.call_status = "disconnected"
            st.session_state.messages = []
            st.rerun()

    st.divider()

    # Chat Transcript History
    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("audio"):
                autoplay = idx == len(st.session_state.messages) - 1 and msg["role"] == "assistant"
                st.audio(msg["audio"], format="audio/mp3", autoplay=autoplay)

    # Real-time Voice Audio Input
    recorded_audio = st.audio_input("Speak to AI Voice Agent:", key=f"voice_in_{st.session_state.audio_key}")

    if recorded_audio:
        audio_bytes = recorded_audio.read()

        with st.spinner("Transcribing speech with Qwen3-ASR-Nepali..."):
            user_text = transcribe_speech(audio_bytes)

        if user_text:
            st.session_state.messages.append({"role": "user", "content": user_text})

            with st.spinner("Thinking via Gemma 4 Open-Source RAG..."):
                rag_res = query_rag_llm(user_text)
                answer = rag_res["answer"]

            with st.spinner("Synthesizing voice response..."):
                audio_file = text_to_speech(answer)

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "audio": audio_file
            })
            st.session_state.audio_key += 1
            st.rerun()
