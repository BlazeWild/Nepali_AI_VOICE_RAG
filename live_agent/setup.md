# ⚡ Realtime API Agent — Setup & Execution Guide

This guide covers setting up and executing the **Realtime API Agent** inside `live_agent/`.

---

## 🚀 Running the Realtime API Agent

```bash
# Install dependencies
pip install -r requirements.txt

# Run the live agent application
python live_agent/agent.py
```

---

## 📁 Package Architecture

```text
live_agent/
├── agent.py          # Realtime agent engine
├── liveapp.py        # Streaming API client
├── realtime_app.py   # Realtime UI application interface
├── prompts.py        # Realtime prompts
├── realtime.md       # Realtime protocol specs
└── setup.md          # Setup documentation
```
