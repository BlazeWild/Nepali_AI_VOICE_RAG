# project info

## models used

**llm**
- qwen2.5:3b via ollama (local, no api key)
- small model so it runs on cpu without crashing. tried qwen3.5:4b but 4gb vram wasnt enough and it kept crashing on cpu too. settled on 2.5:3b as a stable middle ground.

**embeddings**
- intfloat/multilingual-e5-small
- needed multilingual support since the pdf has nepali text. standard english models dont embed devanagari properly. e5 requires `passage:` prefix when indexing and `query:` prefix when searching.

**stt**
- faster-whisper with large-v3-turbo
- tried smaller whisper models first but they couldnt handle dialect properly. the user speaks a mix of nepali dialects so the smaller models were transcribing broken text. large-v3-turbo handles it much better.
- added `initial_prompt` from actual db content so whisper is primed with the vocabulary of whatever document is loaded. this helps with dialect words a lot.

**tts**
- edge-tts with `ne-NP-SagarNeural` voice
- had to use a multilingual neural voice because the answers mix nepali and english words. for example the llm might say a sentence with "PostgreSQL" or "TypeScript" in the middle. a nepali-only voice would break on those. the sagar neural voice handles both without needing to split the text or use separate voices.

---

## pdf extraction

the pdf had nepali text but extracting it directly with pymupdf gave broken unicode — spacing was wrong and some devanagari characters werent recognized properly.

tried two approaches:
1. direct unicode extraction with pymupdf — fast but spacing was off, conjunct characters sometimes broken
2. tesseract ocr at 300dpi with nep+eng language — slower but accurate character recognition

final approach: used `page.get_textpage_ocr()` with tesseract which handles word boundaries natively through `extractDICT()`. this gave proper spacing and correct character rendering without needing any manual post-processing or dictionaries.

sample — broken unicode extraction:
```
अर्जनु शमार् काठमाण्ड ौमा बस्छन्
```

sample — after ocr with tessearct:
```
अर्जुन शर्मा काठमाडौंमा बस्छन्।
```

---

## chunking

used sliding window chunking with `CHUNK_SIZE=500` characters and `CHUNK_OVERLAP=100`.

the overlap is important because if a sentence about a person spans a chunk boundary, a query about that person should still retrieve the relevant chunk. without overlap you lose context at the edges.

sample chunk 1 (page 1):
```
अर्जुन शर्मा एक अनुभवी सफ्टवेयर इन्जिनियर हुन् जसले काठमाडौंमा काम गर्छन्। उनको मुख्य क्षेत्र सफ्टवेयर आर्किटेक्चर, स्वचालन...
```

sample chunk 2 (overlaps with chunk 1 end):
```
...स्वचालन तथा इन्टरप्राइज एप्लिकेसन विकास हो। उनलाई मनपर्ने खाना मोमो र थकाली दालभात हो।
```

this way a query about his food preference still retrieves the right chunk even though the sentence spans two chunks.

---

## llm issues and fixes

since qwen2.5:3b is a small model and the stt transcription isnt perfect (dialect, fast speech), there were a few problems:

**problem: llm dumping all context**
the model was reading the whole retrieved chunk and writing everything it found — food, sport, job, location all in one answer. fixed by being very explicit in the system prompt with bad/good examples showing it should only answer what was asked.

**problem: incomplete answers**
the opposite — prompt said "one piece of information" so it picked only the first food item and dropped the rest. fixed by changing it to "all relevant items that answer the question".

**problem: gibberish from stt mismatch**
when the stt transcribed dialect speech, names got garbled ("अर्जुन" → "पर दुन सर्मा"). the embedding query then returned wrong chunks. fixed by increasing TOP_K to 4 so more context is retrieved, and by telling the llm in the system prompt that the question may have stt errors and to try to understand intent.

**problem: answers with markdown junk**
model sometimes added `---` or `###` in the response. added regex cleanup after the llm response to strip those before passing to tts.

---

## resource limitations

everything here runs locally — no cloud apis, no paid inference. that comes with some tradeoffs.

the whisper large-v3-turbo model is heavy on cpu. the embedding model loads into ram. ollama runs qwen2.5:3b also in ram/cpu. running all three at the same time on a mid-range laptop caused frequent crashes early on, especially when ollama was loading a bigger model like qwen3.5:4b.

fixes that helped:
- switched to qwen2.5:3b which is smaller (1.9gb) and more stable
- streamlit caches the whisper and embedding models with `@st.cache_resource` so they load once and stay in memory instead of reloading on every request
- ran ollama as a background service so it manages its own memory separately from the python process

still, on first load its slow. once everything is warm it runs fine.

---

## other fixes

**hardcoded paths**
early on the pdf path and a few other paths were written as full absolute paths like `/home/blaze/...`. obviously breaks on any other machine. fixed by using `os.path.join(os.path.dirname(__file__), ...)` everywhere so paths are relative to the file location.

also had some hardcoded values in the whisper initial_prompt that were specific to the nepali biography pdf. changed it to pull a sample from whatever is in chromadb instead, so it works with any document.

**system prompt tuning**
the llm system prompt went through a lot of iterations. early versions were too strict (only one item in answer), then too loose (dumping all context). also had the model occasionally outputting markdown formatting which would get read aloud by tts. took a few rounds of writing good/bad examples in the prompt before it behaved properly.

---

## notes on development

used an ai assistant (claude/antigravity) for parts of this — mainly for debugging the prompt engineering, fixing the stt pipeline, and writing the documentation. the core decisions around model selection, chunking strategy, and architecture were figured out through trial and error while building it.
