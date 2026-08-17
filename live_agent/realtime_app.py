"""
realtime_app.py — Streamlit frontend for Real-Time Nepali Voice RAG Agent

Connects to the FastAPI WebSocket backend (backend/server.py) at ws://localhost:8000.
Audio is captured via st.audio_input, sent to backend, and streaming audio chunks
are received and played as they arrive sentence by sentence.
"""

import streamlit as st
import asyncio
import websockets
import base64
import json
import tempfile
import os

BACKEND_WS_URL = "ws://localhost:8000/ws/realtime"
BACKEND_HTTP_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Nepali Voice RAG — Real-Time",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }
.stApp {
    background: radial-gradient(circle at 50% 40%, #1a0533 0%, #0f0a1e 50%, #030712 100%) !important;
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
    width: 150px;
    height: 150px;
    border-radius: 50%;
    background: linear-gradient(135deg, #7c3aed, #4f46e5);
    border: 3px solid #a78bfa;
    box-shadow: 0 0 60px rgba(124,58,237,0.6);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    animation: glowPulse 2.2s infinite;
}
.orb-element.listening {
    background: linear-gradient(135deg, #ef4444, #dc2626);
    border-color: #fca5a5;
    box-shadow: 0 0 60px rgba(239,68,68,0.7);
    animation: glowPulseRed 0.8s infinite;
}
.orb-element.thinking {
    background: linear-gradient(135deg, #f59e0b, #d97706);
    border-color: #fcd34d;
    box-shadow: 0 0 60px rgba(245,158,11,0.7);
}
.orb-element.speaking {
    background: linear-gradient(135deg, #10b981, #047857);
    border-color: #34d399;
    box-shadow: 0 0 60px rgba(16,185,129,0.7);
    animation: glowPulse 0.5s infinite;
}
@keyframes glowPulse {
    0%,100% { box-shadow: 0 0 40px rgba(124,58,237,0.45); }
    50% { box-shadow: 0 0 80px rgba(124,58,237,0.85); }
}
@keyframes glowPulseRed {
    0%,100% { box-shadow: 0 0 40px rgba(239,68,68,0.6); transform: scale(1); }
    50% { box-shadow: 0 0 90px rgba(239,68,68,0.9); transform: scale(1.03); }
}
.status-pill {
    display: inline-block;
    padding: 6px 22px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 600;
    background: rgba(30,41,59,0.8);
    border: 1px solid rgba(124,58,237,0.5);
    color: #a78bfa;
    box-shadow: 0 0 14px rgba(124,58,237,0.3);
    margin-bottom: 14px;
}
.transcript-box {
    background: rgba(30,41,59,0.6);
    border: 1px solid rgba(124,58,237,0.3);
    border-radius: 12px;
    padding: 12px 18px;
    margin: 8px 0;
    font-size: 15px;
    line-height: 1.6;
}
.latency-badge {
    font-size: 11px;
    color: #64748b;
    margin-top: 4px;
}
.sentence-stream {
    color: #a78bfa;
    font-style: italic;
    font-size: 14px;
}
</style>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────────────────────
for key, val in [
    ("call_status", "disconnected"),
    ("messages", []),
    ("audio_key", 0),
    ("streaming_text", ""),
    ("backend_ready", False),
]:
    if key not in st.session_state:
        st.session_state[key] = val


# ── Backend Health Check ───────────────────────────────────────────────────────
def check_backend():
    try:
        import requests
        r = requests.get(f"{BACKEND_HTTP_URL}/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


# ── WebSocket Streaming Call ───────────────────────────────────────────────────
async def stream_voice_pipeline(audio_bytes: bytes):
    """
    Send audio to WebSocket backend and receive streaming events.
    Yields events: {type, data, ...}
    """
    async with websockets.connect(BACKEND_WS_URL, max_size=50_000_000) as ws:
        await ws.send(audio_bytes)

        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=120)
                event = json.loads(msg)
                yield event
                if event.get("type") in ("done", "error"):
                    break
            except asyncio.TimeoutError:
                yield {"type": "error", "data": "Pipeline timed out"}
                break


def run_streaming_sync(audio_bytes: bytes):
    """Run the WebSocket pipeline synchronously, collecting all events."""
    events = []

    async def collect():
        async for event in stream_voice_pipeline(audio_bytes):
            events.append(event)

    asyncio.run(collect())
    return events


# ── UI ─────────────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='text-align:center;margin-top:10px;'>🎙️ Nepali Voice RAG Agent</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<p style='text-align:center;color:#94a3b8;'>Real-Time Streaming · qwen2.5:14b · Qwen3-ASR · Edge-TTS</p>",
    unsafe_allow_html=True
)

backend_ok = check_backend()

# ── Disconnected state ─────────────────────────────────────────────────────────
if st.session_state.call_status == "disconnected":
    if not backend_ok:
        st.error(
            "⚠️ Backend server is not running. Start it with:\n\n"
            "```bash\npython -m uvicorn backend.server:app --host 0.0.0.0 --port 8000\n```"
        )
    else:
        st.success("✅ Backend connected — models loaded and ready")

    st.markdown("""
    <div class="orb-container">
        <div class="status-pill" style="color:#94a3b8;border-color:#334155;">
            Click Start Call to Begin
        </div>
        <div class="orb-element">
            <div style="font-size:36px">📞</div>
            <div style="font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#fff">Ready</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("📞 Start Call", type="primary", use_container_width=True, disabled=not backend_ok):
            st.session_state.call_status = "connecting"
            st.rerun()

# ── Connecting state ───────────────────────────────────────────────────────────
elif st.session_state.call_status == "connecting":
    st.markdown("""
    <div class="orb-container">
        <div class="status-pill">Connecting...</div>
        <div class="orb-element">
            <div style="font-size:36px">🔄</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Synthesize greeting via backend TTS directly (edge-tts local)
    from speech import text_to_speech
    greeting = "नमस्कार! म तपाईंलाई के सहयोग गर्न सक्छु होला?"
    greeting_audio = text_to_speech(greeting)
    st.session_state.messages = [
        {"role": "assistant", "content": greeting, "audio": greeting_audio, "sentences": [greeting]}
    ]
    st.session_state.call_status = "connected"
    st.rerun()

# ── Connected state ────────────────────────────────────────────────────────────
elif st.session_state.call_status == "connected":
    col_a, col_b, col_c = st.columns([1, 3, 1])

    with col_b:
        st.markdown("""
        <div class="orb-container">
            <div class="status-pill">🟢 Connected — AI Voice Agent Active</div>
            <div class="orb-element">
                <div style="font-size:36px;margin-bottom:4px">📞</div>
                <div style="font-size:11px;font-weight:700;letter-spacing:1.5px;
                            text-transform:uppercase;color:#fff">Live</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_c:
        if st.button("❌ End Call", type="primary", use_container_width=True):
            st.session_state.call_status = "disconnected"
            st.session_state.messages = []
            st.rerun()

    st.divider()

    # ── Chat Transcript History ──────────────────────────────────────────────
    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("audio"):
                autoplay = (idx == len(st.session_state.messages) - 1
                            and msg["role"] == "assistant")
                st.audio(msg["audio"], format="audio/mp3", autoplay=autoplay)
            if msg.get("latency"):
                st.markdown(
                    f"<div class='latency-badge'>⏱ {msg['latency']}</div>",
                    unsafe_allow_html=True
                )

    # ── Voice Input ──────────────────────────────────────────────────────────
    recorded_audio = st.audio_input(
        "🎤 Speak now (recording will process automatically):",
        key=f"voice_in_{st.session_state.audio_key}"
    )

    if recorded_audio:
        import time
        audio_bytes = recorded_audio.read()

        st.session_state.messages.append({
            "role": "user",
            "content": "🎤 *Processing audio...*"
        })

        # Use streaming pipeline via WebSocket backend
        status_placeholder = st.empty()
        transcript_placeholder = st.empty()
        response_placeholder = st.empty()
        audio_placeholders = []

        if backend_ok:
            status_placeholder.info("🔄 Sending to Qwen3-ASR for transcription...")
            t_total_start = time.time()

            # Collect streaming events
            events = run_streaming_sync(audio_bytes)

            transcript = ""
            full_response = ""
            audio_chunks = []

            for event in events:
                etype = event.get("type")
                edata = event.get("data", "")

                if etype == "transcript":
                    transcript = edata
                    # Update the user message with actual transcript
                    st.session_state.messages[-1] = {
                        "role": "user",
                        "content": transcript
                    }
                    transcript_placeholder.markdown(
                        f"<div class='transcript-box'>📝 <b>You:</b> {transcript}</div>",
                        unsafe_allow_html=True
                    )
                    status_placeholder.info("💭 Generating response...")

                elif etype == "audio":
                    audio_data = base64.b64decode(edata)
                    audio_chunks.append({
                        "bytes": audio_data,
                        "sentence": event.get("sentence", "")
                    })

                elif etype == "done":
                    full_response = edata

            # Combine all sentence audio bytes into one complete response MP3
            all_audio_bytes = b"".join(chunk["bytes"] for chunk in audio_chunks)
            if all_audio_bytes:
                b64_audio = base64.b64encode(all_audio_bytes).decode()
                main_audio = f"data:audio/mp3;base64,{b64_audio}"
            else:
                main_audio = None

            t_total = time.time() - t_total_start
            latency_str = f"Total: {t_total:.1f}s | {len(audio_chunks)} sentence(s) streamed"

            status_placeholder.empty()
            transcript_placeholder.empty()
            response_placeholder.empty()

            st.session_state.messages.append({
                "role": "assistant",
                "content": full_response or "माफ गर्नुहोला, मसँग यस विषयमा जानकारी उपलब्ध छैन।",
                "audio": main_audio,
                "latency": latency_str
            })

        else:
            # Fallback: use local pipeline directly (no streaming)
            from speech import transcribe_speech, text_to_speech
            from rag import query_rag_llm

            status_placeholder.warning("⚠️ Backend offline — using local sequential pipeline")

            t0 = time.time()
            transcript = transcribe_speech(audio_bytes)
            t_stt = time.time() - t0

            if transcript:
                st.session_state.messages[-1] = {"role": "user", "content": transcript}
                t1 = time.time()
                rag_res = query_rag_llm(transcript)
                answer = rag_res["answer"]
                t_rag_llm = time.time() - t1

                t2 = time.time()
                audio_file = text_to_speech(answer)
                t_tts = time.time() - t2

                status_placeholder.empty()
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "audio": audio_file,
                    "latency": f"STT: {t_stt:.1f}s | LLM: {t_rag_llm:.1f}s | TTS: {t_tts:.1f}s"
                })

        st.session_state.audio_key += 1
        st.rerun()
