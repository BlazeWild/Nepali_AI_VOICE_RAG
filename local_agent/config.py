import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# LLM Config (Set to True for Gemini API, False for local Ollama)
USE_GEMINI = True
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:12b")

# STT Config
WHISPER_MODEL_NAME = "large-v3"
WHISPER_COMPUTE_TYPE = "float16"

# RAG & Chroma Config
CHROMA_PATH = os.path.join(PROJECT_ROOT, "chroma_db")
COLLECTION_NAME = "nepali_pdf"
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
TOP_K = 4

# TTS Config
TTS_VOICE = "ne-NP-SagarNeural"
FALLBACK = "माफ गर्नुहोला, मसँग त्यो क्षेत्रको जानकारी उपलब्ध छैन। मसँग प्रविधि र सफ्टवेयर विकास क्षेत्रका व्यक्तिहरूबारे जानकारी उपलब्ध छ। के हजुर उहाँहरूबारे जान्न चाहनुहुन्छ?"
