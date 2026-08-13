import os

BASE_DIR = os.path.dirname(__file__)

CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")
COLLECTION_NAME = "nepali_pdf"

EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

OLLAMA_MODEL = "qwen2.5:3b"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

WHISPER_MODEL_SIZE = "large-v3-turbo"
TTS_VOICE = "ne-NP-SagarNeural"

TOP_K = 4
FALLBACK = "मलाई यसको जानकारी छैन।"
