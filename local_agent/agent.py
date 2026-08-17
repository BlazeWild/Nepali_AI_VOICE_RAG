import re
import time
import asyncio
import base64
from local_agent.stt.stt_engine import STTEngine
from local_agent.llm.llm_provider import LLMProvider
from local_agent.rag.rag_engine import RAGEngine
from local_agent.tts.tts_engine import TTSEngine
from local_agent.vad.vad_engine import EnergyVAD
from local_agent.prompt2 import SYSTEM_PROMPT
from local_agent.config import FALLBACK

_SENTENCE_RE = re.compile(r'(?<=[।?!\n])\s*')

def split_sentences(buffer: str) -> tuple[list[str], str]:
    parts = _SENTENCE_RE.split(buffer)
    if len(parts) <= 1:
        return [], buffer
    complete = [s.strip() for s in parts[:-1] if s.strip()]
    return complete, parts[-1]


class NepaliVoiceAgent:
    def __init__(self, greeting_text: str = "नमस्कार! म तपाईंलाई के सहयोग गर्न सक्छु होला?"):
        self.greeting_text = greeting_text
        self.stt = STTEngine()
        self.llm = LLMProvider()
        self.rag = RAGEngine()
        self.tts = TTSEngine()
        self.vad = EnergyVAD()

    def preload_models(self):
        print("[Agent] Preloading STT and RAG models on GPU...")
        self.stt.load_model()
        self.rag.load_engine()
        print("[Agent] All GPU models preloaded and ready!")

    async def get_greeting(self) -> tuple[str, bytes | None]:
        """Synthesize initial agent spoken greeting."""
        if not self.greeting_text:
            return "", None
        audio_bytes = await self.tts.synthesize(self.greeting_text)
        return self.greeting_text, audio_bytes

    async def process_turn(
        self,
        audio_bytes: bytes,
        chat_history: list,
        cancel_event: asyncio.Event,
        send_event
    ):
        loop = asyncio.get_event_loop()

        # 1. STT Transcription
        await send_event({"type": "status", "data": "Transcribing..."})
        t0 = time.perf_counter()
        transcript = await loop.run_in_executor(None, self.stt.transcribe, audio_bytes)
        t_stt_ms = (time.perf_counter() - t0) * 1000

        if not transcript or not transcript.strip():
            await send_event({"type": "status", "data": "Ready — speak into microphone"})
            return

        await send_event({
            "type": "transcript",
            "data": transcript,
            "latency_ms": round(t_stt_ms)
        })
        print(f"[Turn] STT: '{transcript}' ({t_stt_ms:.0f}ms)")

        if cancel_event.is_set():
            return

        # 2. RAG Context Retrieval
        await send_event({"type": "status", "data": "Searching knowledge base..."})
        t_rag = time.perf_counter()
        context, docs = await loop.run_in_executor(None, self.rag.retrieve_context, transcript, chat_history)
        t_rag_ms = (time.perf_counter() - t_rag) * 1000

        await send_event({
            "type": "rag_done",
            "data": len(docs),
            "latency_ms": round(t_rag_ms)
        })

        if cancel_event.is_set():
            return

        # 3. LLM + Streaming TTS
        await send_event({"type": "status", "data": "Generating response..."})

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in chat_history[-8:]:
            messages.append(msg)

        if context and context != "NO_RELEVANT_CONTEXT":
            user_prompt_content = f"उपलब्ध जानकारी (CONTEXT):\n{context}\n\nप्रयोगकर्ताको प्रश्न: {transcript}"
        else:
            user_prompt_content = transcript

        messages.append({"role": "user", "content": user_prompt_content})
        chat_history.append({"role": "user", "content": transcript})

        token_queue: asyncio.Queue = asyncio.Queue()

        def token_producer():
            for token in self.llm.stream_tokens(messages, cancel_event):
                loop.call_soon_threadsafe(token_queue.put_nowait, token)
            loop.call_soon_threadsafe(token_queue.put_nowait, None)

        # Fix: run_in_executor returns a Future, not a coroutine
        producer_task = loop.run_in_executor(None, token_producer)
        t_llm_start = time.perf_counter()
        first_token_time = None

        token_buffer = ""
        full_response = ""
        in_think = False

        while True:
            if cancel_event.is_set():
                producer_task.cancel()
                break

            try:
                token = await asyncio.wait_for(token_queue.get(), timeout=30)
            except asyncio.TimeoutError:
                print("[LLM] Timeout waiting for token")
                break

            if token is None:
                break

            if first_token_time is None:
                first_token_time = time.perf_counter()
                ttft_ms = (first_token_time - t_llm_start) * 1000
                print(f"[LLM] TTFT: {ttft_ms:.0f}ms")
                await send_event({"type": "llm_started", "latency_ms": round(ttft_ms)})

            if "<think>" in token or in_think:
                token_buffer += token
                if "</think>" in token_buffer:
                    token_buffer = token_buffer.split("</think>", 1)[-1]
                    in_think = False
                else:
                    in_think = True
                continue

            token_buffer += token
            full_response += token
            await send_event({"type": "token", "data": token})

            complete_sentences, leftover = split_sentences(token_buffer)
            if complete_sentences:
                token_buffer = leftover
                for sentence in complete_sentences:
                    if cancel_event.is_set():
                        break
                    if sentence.strip():
                        audio = await self.tts.synthesize(sentence)
                        if audio and not cancel_event.is_set():
                            await send_event({
                                "type": "audio",
                                "sentence": sentence,
                                "data": base64.b64encode(audio).decode()
                            })

        remaining = token_buffer.strip()
        if remaining and not cancel_event.is_set():
            audio = await self.tts.synthesize(remaining)
            if audio:
                await send_event({
                    "type": "audio",
                    "sentence": remaining,
                    "data": base64.b64encode(audio).decode()
                })

        if not full_response.strip() and not cancel_event.is_set():
            full_response = FALLBACK
            fallback_audio = await self.tts.synthesize(FALLBACK)
            await send_event({
                "type": "audio",
                "sentence": FALLBACK,
                "data": base64.b64encode(fallback_audio).decode() if fallback_audio else ""
            })

        if full_response.strip() and not cancel_event.is_set():
            chat_history.append({"role": "assistant", "content": full_response})
            total_ms = (time.perf_counter() - t0) * 1000
            print(f"[Turn] Complete: '{full_response[:40]}...' ({total_ms:.0f}ms total)")
            await send_event({"type": "done", "data": full_response, "total_ms": round(total_ms)})


# Global agent instance
agent = NepaliVoiceAgent()
