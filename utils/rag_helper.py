# api/utils/rag_helper.py
# PDF upload, chunking, embedding, and semantic search via ChromaDB

import os
import uuid
import numpy as np
# Compatibility shim for NumPy 2.0 where np.float_ was removed
if not hasattr(np, "float_"):
    np.float_ = np.float64
import chromadb
from chromadb.config import Settings

from chromadb.utils import embedding_functions
_ef = embedding_functions.DefaultEmbeddingFunction()

os.environ["ANONYMIZED_TELEMETRY"] = "False"
# Persistent ChromaDB store
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_store")
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH, settings=Settings(anonymized_telemetry=False))

def get_collection(user_id: int):
    """Get or create a per-user ChromaDB collection."""
    name = f"user_{user_id}_docs"
    return chroma_client.get_or_create_collection(
        name=name,
        embedding_function=_ef,
        metadata={"hnsw:space": "cosine"}
    )

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    """Split text into overlapping chunks for better retrieval."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks

def embed_text(texts: list) -> list:
    """Generate embeddings for a list of text strings using default model."""
    return _ef(texts)

def extract_text_from_file(file_path: str) -> str:
    """Extract text from a PDF or plain text file."""
    text = ""
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception:
        # Fallback: read as plain text
        try:
            with open(file_path, "r", errors="ignore") as f:
                text = f.read()
        except Exception:
            pass
    return text

def ingest_document(user_id: int, doc_id: int, file_path: str, file_name: str, pre_extracted_text: str = None) -> int:
    """Parse a PDF/text file, chunk it, embed it, and store in ChromaDB.
    Returns number of chunks stored.
    """
    try:
        if pre_extracted_text is not None:
            text = pre_extracted_text
        else:
            text = extract_text_from_file(file_path)

        if not text.strip():
            return 0

        chunks = chunk_text(text)
        if not chunks:
            return 0

        embeddings = embed_text(chunks)
        collection = get_collection(user_id)

        ids = [f"doc_{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"doc_id": doc_id, "file_name": file_name, "chunk_index": i} for i in range(len(chunks))]

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas
        )
        return len(chunks)
    except Exception as e:
        print(f"RAG ingest error: {e}")
        return 0

def search_documents(user_id: int, query: str, top_k: int = 5) -> list:
    """Semantic search: embed query, find top‑k similar chunks.
    Returns list of text strings.
    """
    try:
        collection = get_collection(user_id)
        if collection.count() == 0:
            return []

        query_embedding = _ef([query])[0]
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count())
        )
        return results.get("documents", [[]])[0]
    except Exception as e:
        print(f"RAG search error: {e}")
        return []

def delete_document_chunks(user_id: int, doc_id: int):
    """Remove all chunks for a specific document from the collection."""
    try:
        collection = get_collection(user_id)
        collection.delete(where={"doc_id": doc_id})
    except Exception:
        pass
