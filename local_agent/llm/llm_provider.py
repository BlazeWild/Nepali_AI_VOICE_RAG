import os
import json
import urllib.request
import asyncio
from local_agent.config import USE_GEMINI, GEMINI_API_KEY, GEMINI_MODEL, OLLAMA_URL, OLLAMA_MODEL

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class LLMProvider:
    def __init__(self):
        self.use_gemini = USE_GEMINI
        self.gemini_key = GEMINI_API_KEY
        self.gemini_model = GEMINI_MODEL
        self.ollama_url = OLLAMA_URL
        self.ollama_model = OLLAMA_MODEL
        self.client = None

        if self.use_gemini and self.gemini_key and HAS_GENAI:
            try:
                self.client = genai.Client(api_key=self.gemini_key)
            except Exception as e:
                print(f"[LLM] genai client init error: {e}")

    def stream_tokens(self, messages: list, cancel_event: asyncio.Event = None):
        if self.use_gemini and self.gemini_key:
            yield from self._stream_gemini_sdk(messages, cancel_event)
        else:
            yield from self._stream_ollama(messages, cancel_event)

    def _stream_gemini_sdk(self, messages: list, cancel_event: asyncio.Event = None):
        print(f"[LLM] streaming via Google GenAI SDK ({self.gemini_model})...")

        system_text = None
        contents = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                system_text = content
            elif role == "user":
                if HAS_GENAI:
                    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=content)]))
                else:
                    contents.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                if HAS_GENAI:
                    contents.append(types.Content(role="model", parts=[types.Part.from_text(text=content)]))
                else:
                    contents.append({"role": "model", "parts": [{"text": content}]})

        try:
            if HAS_GENAI and self.client:
                config = types.GenerateContentConfig(
                    system_instruction=system_text,
                    temperature=0.3,
                    max_output_tokens=200,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
                )
                response = self.client.models.generate_content_stream(
                    model=self.gemini_model,
                    contents=contents,
                    config=config
                )
                for chunk in response:
                    if cancel_event and cancel_event.is_set():
                        break
                    if chunk.text:
                        yield chunk.text
            else:
                yield from self._stream_gemini_http(system_text, messages, cancel_event)
        except Exception as e:
            print(f"[GenAI SDK Error] {e}. Falling back to Ollama...")
            yield from self._stream_ollama(messages, cancel_event)

    def _stream_gemini_http(self, system_text: str, messages: list, cancel_event: asyncio.Event = None):
        contents = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                contents.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})

        payload = {
            "contents": contents,
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 200}
        }
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:streamGenerateContent?alt=sse&key={self.gemini_key}"
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})

        with urllib.request.urlopen(req, timeout=30) as resp:
            for line_bytes in resp:
                if cancel_event and cancel_event.is_set():
                    break
                line = line_bytes.decode("utf-8").strip()
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str:
                        chunk = json.loads(data_str)
                        for candidate in chunk.get("candidates", []):
                            for part in candidate.get("content", {}).get("parts", []):
                                text = part.get("text", "")
                                if text:
                                    yield text

    def _stream_ollama(self, messages: list, cancel_event: asyncio.Event = None):
        print(f"[LLM] streaming via local Ollama ({self.ollama_model})...")
        payload = {
            "model": self.ollama_model,
            "messages": messages,
            "stream": True,
            "keep_alive": "60m",
            "options": {"num_gpu": 99, "temperature": 0.3, "num_predict": 180, "num_ctx": 1024}
        }
        try:
            req = urllib.request.Request(self.ollama_url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                for line in resp:
                    if cancel_event and cancel_event.is_set():
                        break
                    if line:
                        data = json.loads(line.decode("utf-8"))
                        token = data.get("message", {}).get("content", "")
                        if token:
                            yield token
        except Exception as e:
            print(f"[Ollama Error] {e}")
            yield f" Error communicating with local LLM: {e} "
