# Realtime Nepali Voice RAG Agent Setup Guide

This guide explains how to install requirements and run the full-duplex realtime Nepali voice agent using LiveKit WebRTC and Gemini Live Realtime API.

## What is LiveKit?

[LiveKit](https://livekit.io/) is an open-source, high-performance WebRTC stack for building real-time audio and video applications.

- **Website**: [https://livekit.io/](https://livekit.io/)
- **Documentation**: [https://docs.livekit.io/](https://docs.livekit.io/)
- **LiveKit Cloud**: [https://cloud.livekit.io/](https://cloud.livekit.io/)

### Environment Setup

Create a `.env` file in the root directory with the following keys:

```env
LIVEKIT_URL=wss://your-livekit-domain.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
GEMINI_API_KEY=your_gemini_api_key
```

### Installing Dependencies

Install all required Python packages using pip:

```bash
pip install -r requirements.txt
```

---

## How to Run

Running the application requires two processes running simultaneously:

### 1. Start the LiveKit Agent Worker

In the first terminal, run the agent worker process:

```bash
python live_agent/agent.py dev
```

### 2. Start the Streamlit Web Application

In a second terminal, launch the Streamlit frontend:

```bash
streamlit run live_agent/liveapp.py
```

---

## Architecture & Flow

1. **Model Pre-warming**: When a call starts, `agent.py` pre-loads the SentenceTransformer embedding model and ChromaDB collection to ensure minimal latency during RAG queries.
2. **WebRTC Connection**: The worker connects to the LiveKit room and initializes the Gemini Realtime Session (`gemini-3.1-flash-live-preview`).
3. **Greeting & Audio Stream**: Native audio tracks are attached directly in the browser with audio spectrum analysis and dynamic orb scaling.
