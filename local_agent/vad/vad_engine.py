import numpy as np
from collections import deque

class EnergyVAD:
    def __init__(self, sample_rate: int = 16000, silence_duration_ms: int = 600):
        self.sample_rate = sample_rate
        self.silence_duration_ms = silence_duration_ms
        self._silence_chunks = 0
        self._speech_detected = False
        self._energy_history = deque(maxlen=50)
        self._noise_floor = 0.001

    def _rms(self, chunk: np.ndarray) -> float:
        return float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)) + 1e-10)

    def _update_noise(self, rms: float):
        if not self._speech_detected:
            self._noise_floor = 0.95 * self._noise_floor + 0.05 * rms

    def process_chunk(self, audio_chunk: np.ndarray) -> dict:
        rms = self._rms(audio_chunk)
        self._energy_history.append(rms)

        ratio = rms / max(self._noise_floor, 1e-8)
        confidence = float(1.0 / (1.0 + np.exp(-2.0 * (ratio - 4.0))))
        confidence = min(max(confidence, 0.0), 1.0)

        # higher threshold to avoid static/breathing
        is_speech = (rms > 0.035) and (ratio > 4.5)

        speech_started = False
        speech_ended = False

        if is_speech:
            if not self._speech_detected:
                speech_started = True
                self._speech_detected = True
            self._silence_chunks = 0
        else:
            self._update_noise(rms)
            if self._speech_detected:
                self._silence_chunks += 1
                chunks_needed = self.silence_duration_ms // 40
                if self._silence_chunks >= chunks_needed:
                    speech_ended = True
                    self._speech_detected = False
                    self._silence_chunks = 0

        return {
            "is_speech": is_speech,
            "confidence": round(confidence, 3),
            "speech_started": speech_started,
            "speech_ended": speech_ended,
        }

    def reset(self):
        self._silence_chunks = 0
        self._speech_detected = False
        self._energy_history.clear()
        self._noise_floor = 0.001
