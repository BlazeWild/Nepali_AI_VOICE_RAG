# 🏠 Local Agent — Setup & Execution Guide

This guide covers setting up, configuring, and executing the standalone **Nepali Voice RAG Local Agent**.

---

## 🛠️ Prerequisites & Installation

1. **Environment Setup**:
   Ensure Python 3.10+ and CUDA GPU drivers are installed on your machine.

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment (`.env`)**:
   Create a `.env` file in the root directory:
   ```env
   USE_GEMINI=true
   GEMINI_API_KEY=your_google_genai_api_key
   GEMINI_MODEL=gemini-3.1-flash-lite
   OLLAMA_MODEL=gemma3:12b
   ```

---

## 🚀 Running the Local Agent

Run the unified entry script from the project root:

```bash
python local_agent/run.py
```

Once started, open your web browser at:
```text
http://localhost:8000
```
Simply **click the central interactive orb (🎙️)** to speak with the assistant.

---

## ⚙️ Key Configuration Options (`local_agent/config.py`)

* **`USE_GEMINI = True`**:
  Uses the official `google-genai` SDK with `gemini-3.1-flash-lite` for high instruction following, natural Nepali generation, and sub-second TTFT.
* **`USE_GEMINI = False`**:
  Operates completely offline using local Ollama (`gemma3:12b`).
* **`WHISPER_MODEL_NAME = "large-v3"`**:
  Faster-Whisper speech recognition fine-tuned for high Nepali accuracy.

---

## 📁 Package Architecture

```text
local_agent/
├── agent.py                 # Core Voice Agent & initial spoken greeting handler
├── server.py                # FastAPI & WebSocket server
├── run.py                   # Unified CLI entry point
├── config.py                # Configuration management
├── prompt2.py               # Conversational System Prompt & domain boundaries
├── problems_and_solutions.md# Model parameter trade-offs & optimization analysis
├── stt/                     # Speech-to-Text engine (Faster-Whisper)
├── llm/                     # LLM Provider (Google GenAI / Ollama)
├── rag/                     # Vector search engine (ChromaDB + E5 Small)
├── tts/                     # Edge-TTS speech synthesizer
├── vad/                     # Energy-based Voice Activity Detector
└── static/                  # Modern Web Visualizer Interface
```

---

## 📑 Related Documentation
* See **[Problems & Solutions Analysis](problems_and_solutions.md)** for details on STT/LLM trade-offs (<15B models) and hardware optimization.
