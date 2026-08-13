import os
import re
import requests
import chromadb
import streamlit as st
from sentence_transformers import SentenceTransformer
from config import (
    CHROMA_PATH, COLLECTION_NAME, EMBEDDING_MODEL,
    OLLAMA_MODEL, OLLAMA_URL, TOP_K, FALLBACK
)

# load prompt from file so its easy to edit without touching code
_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "nepali_rag.txt")
with open(_PROMPT_PATH, encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()


@st.cache_resource
def load_embedder():
    return SentenceTransformer(EMBEDDING_MODEL, device="cpu")


@st.cache_resource
def load_chroma():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_collection(name=COLLECTION_NAME)


def query_rag_llm(question: str) -> dict:
    embedder = load_embedder()
    collection = load_chroma()

    # e5 needs 'query:' prefix when searching
    embedding = embedder.encode(f"query: {question}", normalize_embeddings=True).tolist()
    results = collection.query(query_embeddings=[embedding], n_results=TOP_K)
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    context = "\n\n".join(documents)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION:\n{question}"}
    ]

    res = requests.post(
        OLLAMA_URL,
        json={"model": OLLAMA_MODEL, "messages": messages, "options": {"temperature": 0.1}, "stream": False}
    )
    raw = res.json().get("message", {}).get("content", "").strip()

    answer = raw
    if answer.startswith("ANSWER:"):
        answer = answer.replace("ANSWER:", "", 1).strip()
    # strip any markdown junk the model sometimes adds
    answer = re.sub(r"[#\-=*`>|]{2,}", "", answer).strip().strip('"').strip("'")

    if not answer:
        answer = FALLBACK

    return {"answer": answer, "documents": documents, "metadatas": metadatas}
