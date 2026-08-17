import time
from rag import preload_all_models, query_rag_llm
from speech import transcribe_speech, text_to_speech

print("==================================================")
print("  STEP 1: PRE-LOADING ALL MODELS BEFORE CALL  ")
print("==================================================")
t0 = time.time()
preload_all_models()
preload_time = round(time.time() - t0, 2)
print(f"✅ Total Model Pre-loading Time: {preload_time}s\n")


def test_audio_pipeline(audio_path: str, test_label: str):
    print("==================================================")
    print(f"  RUNNING WARM TEST: {test_label} ({audio_path})")
    print("==================================================")
    
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    # 1. STT Inference
    t0 = time.time()
    transcription = transcribe_speech(audio_bytes)
    stt_time = round(time.time() - t0, 2)

    # 2. LLM RAG Inference
    t0 = time.time()
    result = query_rag_llm(transcription)
    llm_time = round(time.time() - t0, 2)
    answer = result["answer"]

    # 3. TTS Synthesis
    t0 = time.time()
    audio_file = text_to_speech(answer)
    tts_time = round(time.time() - t0, 2)

    total_latency = round(stt_time + llm_time + tts_time, 2)

    print(f"🎙️ STT Transcribed Text: \"{transcription}\"")
    print(f"🤖 LLM Answer: \"{answer}\"")
    print(f"🔊 Generated Audio: {audio_file}")
    print(f"--------------------------------------------------")
    print(f"⏱️ STT Latency:  {stt_time}s")
    print(f"⏱️ LLM Latency:  {llm_time}s")
    print(f"⏱️ TTS Latency:  {tts_time}s")
    print(f"⚡ TOTAL WARM CONVERSATION LATENCY: {total_latency}s\n")


# Warm Run 1: test.mp3
test_audio_pipeline("/home/blaze/Documents/Windows_Backup/Ashok/__WORK/voice_rag/test.mp3", "TEST 1 (test.mp3)")

# Warm Run 2: test2.mp3
test_audio_pipeline("/home/blaze/Documents/Windows_Backup/Ashok/__WORK/voice_rag/test2.mp3", "TEST 2 (test2.mp3)")
