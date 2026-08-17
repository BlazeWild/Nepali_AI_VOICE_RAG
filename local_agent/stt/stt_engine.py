import os
import tempfile
from faster_whisper import WhisperModel
from local_agent.config import WHISPER_MODEL_NAME, WHISPER_COMPUTE_TYPE

class STTEngine:
    def __init__(self):
        self.model = None

    def load_model(self):
        if self.model is None:
            print(f"[STT] loading {WHISPER_MODEL_NAME} ({WHISPER_COMPUTE_TYPE}) on cuda...")
            self.model = WhisperModel(WHISPER_MODEL_NAME, device="cuda", compute_type=WHISPER_COMPUTE_TYPE)
            print("[STT] model loaded!")
        return self.model

    def transcribe(self, audio_bytes: bytes) -> str:
        if not audio_bytes or len(audio_bytes) < 1000:
            return ""

        model = self.load_model()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio_bytes)
            tmp_path = f.name

        try:
            segments, info = model.transcribe(
                tmp_path,
                language="ne",
                beam_size=5,
                temperature=0.0,
                no_repeat_ngram_size=3,
                condition_on_previous_text=False,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=400)
            )
            text = "".join(s.text for s in segments).strip()
        except Exception as e:
            print(f"[STT Error] {e}")
            text = ""
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        return text
