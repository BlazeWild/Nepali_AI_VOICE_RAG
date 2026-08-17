import os
import tempfile
import asyncio
import torch
import edge_tts
import streamlit as st
from config import QWEN_ASR_MODEL, TTS_VOICE

_STT_MODEL_CACHE = None


def load_qwen_asr():
    """Load and cache Qwen3-ASR-Nepali fine-tuned model for Nepali speech recognition."""
    global _STT_MODEL_CACHE
    if _STT_MODEL_CACHE is not None:
        return _STT_MODEL_CACHE

    from qwen_asr import Qwen3ASRModel

    print("Pre-loading Qwen3-ASR-Nepali model...")
    if torch.cuda.is_available():
        try:
            # 8-bit quantization fits in ~1.7GB VRAM safely
            _STT_MODEL_CACHE = Qwen3ASRModel.from_pretrained(
                QWEN_ASR_MODEL,
                load_in_8bit=True,
                device_map="cuda"
            )
        except Exception:
            _STT_MODEL_CACHE = Qwen3ASRModel.from_pretrained(
                QWEN_ASR_MODEL,
                dtype=torch.float16,
                device_map="auto",
                max_memory={0: "2.5GiB", "cpu": "16GiB"}
            )
    else:
        _STT_MODEL_CACHE = Qwen3ASRModel.from_pretrained(
            QWEN_ASR_MODEL,
            dtype=torch.float32,
            device_map="cpu"
        )
    return _STT_MODEL_CACHE


def transcribe_speech(audio_bytes: bytes, language: str = "ne") -> str:
    """Transcribe audio bytes using pre-loaded Qwen3-ASR-Nepali model."""
    if not audio_bytes:
        return ""

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        model = load_qwen_asr()
        results = model.transcribe(tmp_path)
        text = "".join(getattr(r, "text", str(r)) for r in results).strip()
    except Exception as e:
        st.error(f"STT Error: {e}")
        text = ""
    finally:
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
