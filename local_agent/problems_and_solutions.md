# Nepali Voice RAG Assistant — Problems & Solutions Analysis

This document outlines the architectural trade-offs, performance bottlenecks, model limitations, and solutions identified during the development of the real-time Nepali AI Voice RAG Assistant.

---

## 1. LLM Capability Trade-offs (< 15B Parameter Models)

### Problem
Smaller open-weights language models (models under 15B parameters) struggle to simultaneously achieve **accurate Nepali text generation** and **strict instruction following**.

* **Gemma 3 (e.g. Gemma 3 12B)**:
  * *Strength*: Generates natural, fluent Nepali vocabulary and phrasing.
  * *Weakness*: Weak instruction-following capability; fails to consistently adhere to strict prompt constraints (e.g. boundaries, tool calling, stage confirmation).
* **Qwen 2.5 (e.g. Qwen 2.5 14B / 7B)**:
  * *Strength*: Excellent at instruction following and structured JSON output.
  * *Weakness*: Poor and unnatural Nepali text generation; often degrades into Hindi-influenced phrasing or awkward sentence structures.
* **Llama Series (< 15B)**:
  * *Weakness*: Struggles with both fluent Nepali grammar and strict system prompt instruction following when operating under compressed parameter budgets.

---

## 2. Speech-to-Text (STT) Trade-offs: Speed vs. Accuracy

### Problem
* **Whisper Turbo**:
  * *Strength*: Fast processing speed and low inference latency.
  * *Weakness*: Lower transcription accuracy for low-resource languages like Nepali, leading to hallucinations or misrecognized query keywords.
* **Fine-Tuned ASR Models (e.g., faster-whisper large-v3 / Qwen-ASR)**:
  * *Strength*: High accuracy and robust handling of Nepali dialectal nuances.
  * *Weakness*: Higher computational footprint and longer initial inference latency.

---

## 3. Comprehensive Solutions & Architectural Fixes

### Solution Architecture
1. **Larger LLM Parameters & GPU Hardware**:
   * Deploy larger open-weight models (> 15B, 27B, or 70B parameters) or cloud LLM APIs that excel at both complex instruction following and natural Nepali generation.
   * Utilize enterprise GPUs with sufficient VRAM (e.g., NVIDIA A10G / H100 / A100) to keep LLM time-to-first-token (TTFT) sub-second.

2. **Isolated Bottleneck Testing (`USE_GEMINI = True`)**:
   * To verify whether the LLM is the performance/accuracy bottleneck in local setups, set `USE_GEMINI = True` in `local_agent/config.py`.
   * **Google GenAI API (`gemini-3.1-flash-lite`)** serves as a baseline: it strictly adheres to system prompts, produces natural Nepali, and streams tokens at high speeds.

3. **Optimized STT Engine**:
   * Using `faster-whisper` with `large-v3` in `float16` precision on CUDA provides the optimal balance between top-tier Nepali accuracy and real-time streaming throughput.

---

## 4. Summary Table

| Component | Smaller Models (< 15B) | Preferred Production Solution |
| :--- | :--- | :--- |
| **LLM (Nepali Generation)** | Gemma 3 (Good Nepali, Weak Instructions)<br>Qwen 2.5 (Strong Instructions, Poor Nepali) | Cloud API (`Gemini 3.1 Flash Lite`) or Large Open Models (> 27B/70B) on High-VRAM GPUs |
| **STT Engine** | Whisper Turbo (Fast, Inaccurate) | `faster-whisper large-v3` (float16 on CUDA) |
| **RAG Vector Search** | Direct SQL / keyword search | `ChromaDB` + `multilingual-e5-small` embeddings |
