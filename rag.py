import os
import re
import requests
import chromadb
import streamlit as st
from sentence_transformers import SentenceTransformer
from config import (
    CHROMA_PATH, COLLECTION_NAME, EMBEDDING_MODEL,
    OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_URL,
    TOP_K, FALLBACK
)
from prompt2 import SYSTEM_PROMPT

_EMBEDDER_CACHE = None
_CHROMA_COLLECTION_CACHE = None


def load_embedder():
    global _EMBEDDER_CACHE
    if _EMBEDDER_CACHE is None:
        _EMBEDDER_CACHE = SentenceTransformer(EMBEDDING_MODEL, device="cpu")
    return _EMBEDDER_CACHE


def load_chroma():
    global _CHROMA_COLLECTION_CACHE
    if _CHROMA_COLLECTION_CACHE is None:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        _CHROMA_COLLECTION_CACHE = client.get_collection(name=COLLECTION_NAME)
    return _CHROMA_COLLECTION_CACHE


def preload_all_models():
    """Pre-load embedding model, database, and STT model before user starts talking."""
    from speech import load_qwen_asr
    print("Pre-loading Embedding Model...")
    load_embedder()
    print("Pre-loading Vector Database...")
    load_chroma()
    print("Pre-loading Qwen3-ASR STT Model on GPU...")
    load_qwen_asr()
    print("All models pre-loaded and warmed up!")


def query_rag_llm(question: str) -> dict:
    embedder = load_embedder()
    collection = load_chroma()

    # e5 needs 'query:' prefix when searching
    embedding = embedder.encode(f"query: {question}", normalize_embeddings=True).tolist()
    results = collection.query(query_embeddings=[embedding], n_results=TOP_K)
    documents = results["documents"][0] if results.get("documents") else []
    metadatas = results["metadatas"][0] if results.get("metadatas") else []

    context = "\n\n".join(documents) if documents else "No relevant context found."

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION:\n{question}"}
    ]

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    raw = ""

    # OpenRouter Gemma 4 Model List
    models_to_try = [
        "google/gemma-4-26b-a4b-it:free",          # Gemma 4 Open-Source Model
        "google/gemma-4-31b-it:free",             # Gemma 4 31B
        OPENROUTER_MODEL,                         # Configured model
        "z-ai/glm-5.2:free",                      # Open-Source Model
        "openrouter/free"                         # OpenRouter free fallback
    ]

    for model in models_to_try:
        if not model:
            continue
        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.1
            }
            res = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=12)
            res_json = res.json()
            if res.status_code == 200 and "choices" in res_json:
                raw = res_json["choices"][0]["message"]["content"].strip()
                if raw:
                    break
        except Exception:
            continue

    if not raw:
        raw = FALLBACK

    answer = raw
    if answer.startswith("ANSWER:"):
        answer = answer.replace("ANSWER:", "", 1).strip()
    # strip markdown formatting
    answer = re.sub(r"[#\-=*`>|]{2,}", "", answer).strip().strip('"').strip("'")

    if not answer:
        answer = FALLBACK

    return {"answer": answer, "documents": documents, "metadatas": metadatas}
