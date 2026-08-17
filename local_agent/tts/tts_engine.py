import os
import tempfile
import edge_tts
from local_agent.config import TTS_VOICE

class TTSEngine:
    def __init__(self, voice: str = TTS_VOICE):
        self.voice = voice

    async def synthesize(self, text: str) -> bytes | None:
        text = text.strip()
        if not text:
            return None

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                tmp_path = f.name

            communicate = edge_tts.Communicate(text, self.voice, rate="+10%")
            await communicate.save(tmp_path)

            with open(tmp_path, "rb") as f:
                data = f.read()

            if os.path.exists(tmp_path):
                os.remove(tmp_path)

            return data
        except Exception as e:
            print(f"[TTS Error] {e}")
            return None
