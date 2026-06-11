# api/utils/rag_helper.py
# PDF upload, chunking, embedding, and semantic search via ChromaDB

import os
import uuid
import numpy as np
# Compatibility shim for NumPy 2.0 where np.float_ was removed
if not hasattr(np, "float_"):
    np.float_ = np.float64
# pyrefly: ignore [missing-import]
import chromadb
# pyrefly: ignore [missing-import]
from chromadb.config import Settings

# pyrefly: ignore [missing-import]
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
        # pyrefly: ignore [missing-import]
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                # If little or no text is extracted, it might be a scanned image. Use Pixtral OCR.
                if not page_text or len(page_text.strip()) < 50:
                    try:
                        import base64
                        from io import BytesIO
                        import requests
                        
                        im = page.to_image(resolution=150).original
                        buffered = BytesIO()
                        im.save(buffered, format="PNG")
                        img_str = base64.b64encode(buffered.getvalue()).decode()
                        
                        api_key = os.getenv("MISTRAL_API_KEY")
                        if api_key:
                            headers = {
                                "Content-Type": "application/json",
                                "Authorization": f"Bearer {api_key}"
                            }
                            payload = {
                                "model": "pixtral-12b-2409",
                                "messages": [
                                    {
                                        "role": "user",
                                        "content": [
                                            {"type": "text", "text": "Extract all text and tables from this image precisely. Do not add any introductory or concluding text. Just output the extracted content."},
                                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_str}"}}
                                        ]
                                    }
                                ],
                                "max_tokens": 1000
                            }
                            resp = requests.post("https://api.mistral.ai/v1/chat/completions", json=payload, headers=headers, timeout=60)
                            if resp.status_code == 200:
                                page_text = resp.json()["choices"][0]["message"]["content"]
                    except Exception as e:
                        print(f"Pixtral OCR error: {e}")
                        
                text += "\n" + (page_text or "")
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

        results = collection.query(
            query_texts=[query],
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
