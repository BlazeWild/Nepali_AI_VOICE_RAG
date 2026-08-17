import time
import torch
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from local_agent.config import CHROMA_PATH, COLLECTION_NAME, EMBEDDING_MODEL, TOP_K

class RAGEngine:
    def __init__(self):
        self.embedder = None
        self.collection = None

    def load_engine(self):
        if self.embedder is None:
            t0 = time.perf_counter()
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"[RAG] loading embedder {EMBEDDING_MODEL} on {device}...")
            self.embedder = SentenceTransformer(EMBEDDING_MODEL, device=device)
            print(f"[RAG] embedder ready ({(time.perf_counter()-t0)*1000:.0f}ms)")

        if self.collection is None:
            client = chromadb.PersistentClient(
                path=CHROMA_PATH,
                settings=Settings(anonymized_telemetry=False)
            )
            self.collection = client.get_or_create_collection(COLLECTION_NAME)
            print(f"[RAG] ChromaDB collection '{COLLECTION_NAME}' connected ({self.collection.count()} chunks)")

    def retrieve_context(self, question: str, chat_history: list = None) -> tuple[str, list]:
        self.load_engine()
        t0 = time.perf_counter()

        query_vec = self.embedder.encode(question, normalize_embeddings=True).tolist()
        results = self.collection.query(
            query_embeddings=[query_vec],
            n_results=TOP_K
        )

        valid_docs = []
        if results.get("documents") and results.get("distances"):
            docs = results["documents"][0]
            dists = results["distances"][0]
            for doc, dist in zip(docs, dists):
                if dist < 1.35:
                    valid_docs.append(doc)

        context = "\n\n".join(valid_docs) if valid_docs else "NO_RELEVANT_CONTEXT"
        print(f"[RAG] retrieved {len(valid_docs)} chunks in {(time.perf_counter()-t0)*1000:.0f}ms")
        return context, valid_docs
