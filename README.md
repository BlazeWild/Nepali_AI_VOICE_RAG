# voice rag

a local voice-in voice-out rag system in nepali. speak a question, it transcribes, retrieves context from a pdf, generates a nepali answer using a local llm, and speaks it back.

no cloud, no api keys for inference. runs fully offline once set up.

## what it does

- takes voice input via browser mic
- transcribes using faster-whisper (large-v3-turbo)
- retrieves relevant chunks from chromadb using multilingual embeddings
- generates a nepali answer with qwen2.5:3b through ollama
- speaks the answer back using edge-tts (nepali neural voice)

## structure

```
voice_rag/
├── app.py          - streamlit ui
├── config.py       - all constants
├── speech.py       - stt + tts
├── rag.py          - retrieval + llm
├── prompts/
│   └── nepali_rag.txt
└── database/
    └── chunk.py    - pdf ocr + chunking + indexing
```

## setup

see instructions.md
