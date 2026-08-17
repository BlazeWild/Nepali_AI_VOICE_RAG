import base64
import sys
import os
import asyncio
import json
import numpy as np
from collections import deque

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from local_agent.agent import agent
from local_agent.config import USE_GEMINI, GEMINI_MODEL, OLLAMA_MODEL

app = FastAPI(title="Nepali Voice RAG — Real-Time")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(_STATIC_DIR):
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.on_event("startup")
async def startup():
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, agent.preload_models)
    mode = f"Gemini API ({GEMINI_MODEL})" if USE_GEMINI else f"Ollama ({OLLAMA_MODEL})"
    print(f"[Server] Ready. Running LLM mode: {mode}")


@app.get("/")
async def serve_ui():
    index = os.path.join(_STATIC_DIR, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"message": "Nepali Voice RAG API running."}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "llm_mode": "gemini" if USE_GEMINI else "ollama",
        "model": GEMINI_MODEL if USE_GEMINI else OLLAMA_MODEL
    }


@app.websocket("/ws/realtime")
async def ws_realtime(websocket: WebSocket):
    await websocket.accept()
    client = websocket.client
    print(f"[Server] Client connected: {client}")

    vad = agent.vad
    vad.reset()

    pre_speech_buffer: deque = deque(maxlen=10)
    audio_buffer: list[bytes] = []
    cancel_event = asyncio.Event()

    current_turn_task: asyncio.Task | None = None
    last_turn_start_time: float = 0.0
    is_agent_speaking: bool = False

    async def send(event: dict):
        nonlocal is_agent_speaking
        if event.get("type") == "audio":
            is_agent_speaking = True
        elif event.get("type") in ["done", "interrupted", "error"]:
            is_agent_speaking = False
            audio_buffer.clear()
            pre_speech_buffer.clear()
            vad.reset()
        try:
            await websocket.send_json(event)
        except Exception:
            pass

    # Send initial spoken greeting audio when client connects
    try:
        greeting_text, greeting_audio = await agent.get_greeting()
        if greeting_audio:
            await send({
                "type": "audio",
                "sentence": greeting_text,
                "data": base64.b64encode(greeting_audio).decode(),
                "latency_ms": 0
            })
            await send({"type": "done"})
    except Exception as e:
        print(f"[Server] Greeting error: {e}")

    chat_history = []

    async def run_turn(audio_bytes: bytes):
        nonlocal cancel_event
        cancel_event = asyncio.Event()
        try:
            await agent.process_turn(audio_bytes, chat_history, cancel_event, send)
        except asyncio.CancelledError:
            await send({"type": "interrupted"})
        except Exception as e:
            print(f"[Server] Turn error: {e}")
            await send({"type": "error", "data": str(e)})

    try:
        while True:
            msg = await websocket.receive()
            msg_type = msg.get("type")

            if msg_type == "websocket.disconnect":
                print(f"[Server] Client disconnected: {client}")
                break

            if msg_type == "websocket.receive" and msg.get("text"):
                try:
                    ctrl = json.loads(msg["text"])
                    if ctrl.get("type") == "interrupt":
                        print("[Server] Barge-in from client")
                        cancel_event.set()
                        if current_turn_task and not current_turn_task.done():
                            current_turn_task.cancel()
                        audio_buffer.clear()
                        vad.reset()
                        await send({"type": "interrupted"})
                except Exception:
                    pass
                continue

            if msg_type == "websocket.receive" and msg.get("bytes"):
                raw_bytes = msg["bytes"]

                if raw_bytes.startswith(b"RIFF"):
                    try:
                        import wave, io
                        with wave.open(io.BytesIO(raw_bytes), "rb") as wf:
                            frames = wf.readframes(wf.getnframes())
                            i16 = np.frombuffer(frames, dtype=np.int16)
                            pcm = (i16.astype(np.float32) / 32768.0)
                            raw_bytes = pcm.tobytes()
                    except Exception as ex:
                        print(f"[Server] WAV parsing error: {ex}")
                        continue
                else:
                    n_samples = len(raw_bytes) // 4
                    if n_samples < 160:
                        continue
                    pcm = np.frombuffer(raw_bytes, dtype=np.float32)

                vad_result = vad.process_chunk(pcm)
                await send({
                    "type": "vad",
                    "is_speech": vad_result["is_speech"],
                    "confidence": vad_result["confidence"]
                })

                now = asyncio.get_event_loop().time()
                is_turn_busy = current_turn_task and not current_turn_task.done()

                if is_turn_busy or is_agent_speaking:
                    if vad_result["is_speech"]:
                        audio_buffer.append(raw_bytes)
                        if len(audio_buffer) >= 20 and (now - last_turn_start_time > 1.5):
                            print("[Server] User barge-in detected during audio playback!")
                            cancel_event.set()
                            current_turn_task.cancel()
                            audio_buffer.clear()
                            pre_speech_buffer.clear()
                            is_agent_speaking = False
                            await send({"type": "interrupted"})
                    else:
                        audio_buffer.clear()
                        pre_speech_buffer.clear()
                    continue

                if not vad_result["is_speech"] and not vad_result["speech_started"] and not audio_buffer:
                    pre_speech_buffer.append(raw_bytes)

                if vad_result["speech_started"]:
                    audio_buffer.extend(pre_speech_buffer)
                    pre_speech_buffer.clear()
                    audio_buffer.append(raw_bytes)
                elif vad_result["is_speech"]:
                    audio_buffer.append(raw_bytes)

                if vad_result["speech_ended"] and len(audio_buffer) >= 15:
                    if current_turn_task and not current_turn_task.done():
                        audio_buffer.clear()
                        pre_speech_buffer.clear()
                    else:
                        print(f"[Server] Speech ended ({len(audio_buffer)*0.04:.2f}s audio)")
                        all_pcm = b"".join(audio_buffer)
                        audio_buffer.clear()
                        pre_speech_buffer.clear()
                        vad.reset()

                        wav_bytes = _pcm_to_wav(all_pcm, sample_rate=16000)

                        last_turn_start_time = now
                        cancel_event = asyncio.Event()
                        current_turn_task = asyncio.create_task(run_turn(wav_bytes))

    except WebSocketDisconnect:
        print(f"[Server] Client disconnected: {client}")
        if current_turn_task and not current_turn_task.done():
            cancel_event.set()
            current_turn_task.cancel()
    except Exception as e:
        print(f"[Server] WebSocket error: {e}")
        try:
            await send({"type": "error", "data": str(e)})
        except Exception:
            pass


def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 16000) -> bytes:
    import wave
    import io
    pcm_f32 = np.frombuffer(pcm_bytes, dtype=np.float32)
    pcm_i16 = (pcm_f32 * 32767).clip(-32768, 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_i16.tobytes())
    return buf.getvalue()


if __name__ == "__main__":
    uvicorn.run("local_agent.server:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
