# setup

## 1. ollama

install from https://ollama.com, then

```bash
ollama pull qwen2.5:3b
ollama serve
```

## 2. tesseract

needed for nepali ocr. install tesseract with nepali traineddata.
guide here: https://tesseract-ocr.github.io/tessdoc/Installation.html

make sure `nep.traineddata` and `eng.traineddata` are in `database/tessdata/`.

## 3. python

```bash
pip install -r requirements.txt
```

faster-whisper downloads the model on first run (~1.5gb). embedding model is ~120mb. both cache after that.

## 4. index the pdf

put your pdf in `database/`, update `PDF_PATH` in `database/chunk.py`, then

```bash
python database/chunk.py
```

only need to run this once per pdf. it does ocr, chunks, embeds, stores in chromadb.

## 5. run

```bash
streamlit run app.py
```

make sure ollama is running first.
