#!/usr/bin/env python3
import sys
import os
import platform
import socket
import torch
import uvicorn

# Always insert repository root as sys.path[0]
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from local_agent.config import USE_GEMINI, GEMINI_MODEL, OLLAMA_MODEL, WHISPER_MODEL_NAME


def check_port(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def main():
    system_os = platform.system()
    print("=" * 60)
    print("   🇳🇵 REAL-TIME NEPALI VOICE RAG ASSISTANT   ")
    print("=" * 60)
    print(f"✓ OS Platform: {system_os} ({platform.release()})")

    # Check CUDA GPU
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram_mb = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)
        print(f"✓ GPU: {gpu_name} ({vram_mb:.0f} MB VRAM)")
    else:
        print("⚠️ Warning: Running on CPU (no CUDA GPU detected)")

    # Check LLM Configuration
    if USE_GEMINI:
        print(f"✓ LLM Provider: Google GenAI Cloud API ({GEMINI_MODEL})")
    else:
        print(f"✓ LLM Provider: Local Ollama ({OLLAMA_MODEL})")

    print(f"✓ STT Engine: faster-whisper ({WHISPER_MODEL_NAME})")

    port = 8000
    if check_port("127.0.0.1", port):
        print(f"⚠️ Port {port} is currently in use. Uvicorn will rebind...")

    print("=" * 60)
    print(f"Starting Real-Time Server on http://localhost:{port}")
    print("=" * 60)

    uvicorn.run(
        "local_agent.server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
