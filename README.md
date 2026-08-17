# 🇳🇵 Real-Time Nepali AI Voice RAG Assistant

A sub-second, real-time Nepali AI Voice Assistant powered by Retrieval-Augmented Generation (RAG), Speech-to-Text (STT), Large Language Models (LLM), and Text-to-Speech (TTS).

---

## 🛠️ Execution Modes & Setup Guides

### 1. 🏠 Local Agent (`local_agent/`)
* **Quick Start**: `python local_agent/run.py`
* **Setup & Guide**: Refer to **[local_agent/setup.md](local_agent/setup.md)** for installation, environment configuration, and execution instructions.
* **Problems & Solutions**: Refer to **[local_agent/problems_and_solutions.md](local_agent/problems_and_solutions.md)** for in-depth analysis on STT/LLM model parameter limits (<15B models), Nepali generation trade-offs, and hardware optimizations.

### 2. ⚡ Realtime API Agent (`live_agent/`)
* **Setup & Guide**: Refer to **[live_agent/setup.md](live_agent/setup.md)** for setting up and running the WebSocket Realtime API agent.

---

## 🚀 Quick Start (Local Agent)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch Local Agent
python local_agent/run.py
```

Open your browser at `http://localhost:8000` to interact with the assistant.
