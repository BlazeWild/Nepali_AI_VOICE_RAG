import os
import re
import fitz
import chromadb
from sentence_transformers import SentenceTransformer

PDF_PATH = os.path.join(os.path.dirname(__file__), "नमूना_व्यक्तिगत_जीवनी_RAG_DATA_ONLY.pdf")
TESSDATA_DIR = os.path.join(os.path.dirname(__file__), "tessdata")

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
COLLECTION_NAME = "nepali_pdf"
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"


def extract_pdf_with_spatial_ocr(pdf_path: str):
    # reads pdf using pymupdf ocr, nep+eng at 300dpi, fallback to get_text() if needed
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    pages = []

    for page_number, page in enumerate(doc):
        text = ""
        try:
            tp = page.get_textpage_ocr(language="nep+eng", tessdata=TESSDATA_DIR, dpi=300, full=True)
            d = tp.extractDICT()

            output_lines = []
            for block in d.get("blocks", []):
                for line in block.get("lines", []):
                    line_text = ""
                    for span in line.get("spans", []):
                        line_text += span.get("text", "") + " "

                    line_text = line_text.strip()
                    line_text = re.sub(r'[ \t]+', ' ', line_text)  # cleanup extra spaces
                    if line_text:
                        output_lines.append(line_text)

            text = "\n".join(output_lines)
        except Exception as e:
            print(f"OCR warning on page {page_number+1}: {e}, falling back to direct text extraction...")
            text = page.get_text()

        if not text.strip():
            text = page.get_text()

        if text.strip():
            pages.append({"page": page_number + 1, "text": text.strip()})

    doc.close()
    return pages


def create_chunks(pages, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    # sliding window chunking with overlap so context doesnt get cut off badly
    chunks = []
    for page in pages:
        text = page["text"]
        words = text.split()
        if not words:
            continue

        current_words = []
        current_len = 0

        for word in words:
            if current_len + len(word) + 1 > chunk_size and current_words:
                chunk_str = " ".join(current_words)
                chunks.append({"text": chunk_str, "page": page["page"]})

                # keep last few words as overlap for next chunk
                overlap_words = []
                overlap_len = 0
                for w in reversed(current_words):
                    if overlap_len + len(w) + 1 <= overlap:
                        overlap_words.insert(0, w)
                        overlap_len += len(w) + 1
                    else:
                        break
                current_words = overlap_words
                current_len = overlap_len

            current_words.append(word)
            current_len += len(word) + 1

        if current_words:
            chunks.append({"text": " ".join(current_words), "page": page["page"]})

    return chunks


def store_in_chroma(chunks, db_path=CHROMA_PATH, collection_name=COLLECTION_NAME):
    print("\nSTORING CHUNKS IN CHROMADB\n")
    model = SentenceTransformer(EMBEDDING_MODEL)

    client = chromadb.PersistentClient(path=db_path)

    # wipe old collection and start fresh
    try:
        client.delete_collection(name=collection_name)
    except Exception:
        pass
    collection = client.create_collection(name=collection_name)

    # e5 needs 'passage:' prefix for indexing
    passages = [f"passage: {c['text']}" for c in chunks]
    raw_documents = [c["text"] for c in chunks]
    metadatas = [{"page": c["page"]} for c in chunks]
    ids = [f"chunk_page_{c['page']}_{i+1}" for i, c in enumerate(chunks)]

    print(f"encoding {len(chunks)} chunks...")
    embeddings = model.encode(passages, normalize_embeddings=True).tolist()

    collection.upsert(documents=raw_documents, embeddings=embeddings, metadatas=metadatas, ids=ids)
    print(f"done. stored {len(chunks)} chunks in '{collection_name}'\n")


def main():
    print("\nstarting ocr chunking + indexing\n")

    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"pdf not found:\n{PDF_PATH}")

    print("extracting pdf...\n")
    pages = extract_pdf_with_spatial_ocr(PDF_PATH)
    print(f"got {len(pages)} pages\n")

    # print first 2 pages to check extraction looks ok
    for page in pages[:2]:
        print(f"--- page {page['page']} ---")
        print(page["text"])
        print()

    chunks = create_chunks(pages)
    print(f"created {len(chunks)} chunks\n")

    # quick sanity check on first few chunks
    for i, chunk in enumerate(chunks[:5]):
        print(f"--- chunk {i+1} | page {chunk['page']} ---")
        print(chunk["text"])
        print(f"chars: {len(chunk['text'])}\n")

    store_in_chroma(chunks)


if __name__ == "__main__":
    main()