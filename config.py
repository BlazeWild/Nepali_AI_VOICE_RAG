import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(__file__)

CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")
COLLECTION_NAME = "nepali_pdf"

EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

# OpenRouter Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API") or os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen3.6-flash") # or z-ai/glm-5.2:free / qwen/qwen-2.5-72b-instruct
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# STT Model
QWEN_ASR_MODEL = "sidskarki/Qwen3-ASR-Nepali"

# TTS Configuration
TTS_VOICE = "ne-NP-SagarNeural"

TOP_K = 4
FALLBACK = "माफ गर्नुहोला, मसँग यस विषयमा जानकारी उपलब्ध छैन।"
