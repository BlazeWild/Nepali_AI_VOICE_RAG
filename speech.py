import os
import tempfile
import asyncio
import edge_tts
import streamlit as st
from faster_whisper import WhisperModel
from config import WHISPER_MODEL_SIZE, TTS_VOICE


@st.cache_resource
def load_whisper():
    return WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")


def transcribe_speech(audio_bytes: bytes, language: str = "ne") -> str:
    # dump audio bytes to a temp file so whisper can read it
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        f.write(audio_bytes)
        tmp_path = f.name

    model = load_whisper()
    lang_param = language if language != "auto" else None

    # pull a sample from db to prime whisper with actual doc vocabulary
    # helps a lot with dialect words and broken STT
    try:
        from rag import load_chroma
        sample = load_chroma().get(limit=1)
        initial_prompt = sample["documents"][0][:200] if sample["documents"] else None
    except Exception:
        initial_prompt = None

    segments, _ = model.transcribe(
        tmp_path,
        beam_size=10,
        language=lang_param,
        vad_filter=True,
        initial_prompt=initial_prompt
    )
    text = " ".join(s.text for s in segments).strip()

    try:
        os.remove(tmp_path)
    except Exception:
        pass

    return text


async def _synthesize_async(text: str, voice: str) -> str:
    out = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    await edge_tts.Communicate(text, voice).save(out)
    return out


def text_to_speech(text: str, voice: str = TTS_VOICE) -> str | None:
    if not text or not text.strip():
        return None
    try:
        return asyncio.run(_synthesize_async(text, voice))
    except Exception as e:
        st.warning(f"TTS error: {e}")
        return None
