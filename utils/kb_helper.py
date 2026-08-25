import os
import io
import uuid
import json
os.environ["ANONYMIZED_TELEMETRY"] = "False"
import numpy as np
if not hasattr(np, "float_"):
    np.float_ = np.float64
# pyrefly: ignore [missing-import]
import chromadb
# pyrefly: ignore [missing-import]
from chromadb.utils import embedding_functions
# pyrefly: ignore [missing-import]
from arango import ArangoClient
# pyrefly: ignore [missing-import]
import pdfplumber
from PIL import Image
import io
try:
    import pytesseract  # type: ignore[import-untyped]
except Exception:
    pytesseract = None  # type: ignore[assignment]

# Use local llm helper if needed
from utils.local_llm_helper import _chat

# ─── Config ───────────────────────────────────────────────────────────────────
ARANGO_HOST     = os.getenv("ARANGO_HOST", "")
ARANGO_DB       = os.getenv("ARANGO_DB", "")
ARANGO_USERNAME = os.getenv("ARANGO_USERNAME", "")
ARANGO_PASSWORD = os.getenv("ARANGO_PASSWORD", "")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL   = os.getenv("LLM_MODEL") or os.getenv("MISTRAL_MODEL", "mistral-small:24b")
RELEVANCE_THRESHOLD = int(os.getenv("RELEVANCE_THRESHOLD", "70"))

# ─── ChromaDB Setup ───────────────────────────────────────────────────────────
# pyrefly: ignore [missing-import]
from chromadb.config import Settings
CHROMA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_store")
_chroma_client = chromadb.PersistentClient(path=CHROMA_PATH, settings=Settings(anonymized_telemetry=False))
_ef = embedding_functions.DefaultEmbeddingFunction()

kb_collection = _chroma_client.get_or_create_collection(
    name="knowledge_base",
    embedding_function=_ef,
    metadata={"hnsw:space": "cosine"}
)

# ─── ArangoDB Setup ───────────────────────────────────────────────────────────
_arango_client = ArangoClient(hosts=ARANGO_HOST)
_db = None
try:
    # First connect to _system to check/create the database
    _sys_db = _arango_client.db("_system", username=ARANGO_USERNAME, password=ARANGO_PASSWORD)
    
    db_name = ARANGO_DB if ARANGO_DB else "_system"
    if db_name != "_system" and not _sys_db.has_database(db_name):
        print(f"[INFO] ArangoDB '{db_name}' not found. Creating it automatically...")
        _sys_db.create_database(db_name)
        
    _db = _arango_client.db(db_name, username=ARANGO_USERNAME, password=ARANGO_PASSWORD)
except Exception as e:
    print(f"Failed to connect to or create ArangoDB: {e}")

def init_arango_collections():
    if not _db: return
    if not _db.has_collection("kb_nodes"):
        _db.create_collection("kb_nodes")
    if not _db.has_collection("kb_edges"):
        _db.create_collection("kb_edges", edge=True)

# Initialize collections
init_arango_collections()

# ─── Helper Functions ─────────────────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text

def extract_text_from_image(file_bytes: bytes) -> str:
    """Try OCR on common image formats using pytesseract (if available)."""
    if pytesseract is None:
        return ""
    try:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        text = pytesseract.image_to_string(img)
        return text
    except Exception as e:
        print(f"Image OCR failed: {e}")
        return ""

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list:
    # pyrefly: ignore [missing-import]
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    return text_splitter.split_text(text)

def extract_kg_from_text(text: str) -> dict:
    """Extract Nodes and Edges using LLM."""
    system = (
        "Extract entities and relationships from this text to build a Knowledge Graph.\n"
        "Return ONLY valid JSON in this format: {\"nodes\": [{\"id\": \"Entity1\", \"type\": \"Person/Company/Document/etc\"}], \"edges\": [{\"_from\": \"Entity1\", \"_to\": \"Entity2\", \"label\": \"owns\"}]}\n"
        "Do NOT return any other text, just JSON."
    )
    
    # We use local _chat fallback if MISTRAL_API_KEY is not set or we prefer local mistral
    try:
        resp = _chat(model=None, messages=[{"role": "system", "content": system}, {"role": "user", "content": text[:4000]}], max_tokens=1000, temperature=0.1)
        content = resp["choices"][0]["message"]["content"].strip()
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print(f"LLM Extraction failed: {e}")
        return {"nodes": [], "edges": []}

def assess_document_relevance(text: str) -> dict:
    """Assess if the document is relevant for the knowledge base (insurance policy, claim form, company manual)."""
    system = (
        "You are an AI document evaluator. Read the provided document text and determine how relevant it is to an insurance company's knowledge base (policies, claim forms, company manuals, SOPs).\n"
        "Return ONLY a JSON object with a 'score' field containing an integer between 0 and 100, and a 'reason' field explaining why you gave this score. Do NOT return any other text.\n"
        "Example: {\"score\": 85, \"reason\": \"The document discusses insurance policies...\"}"
    )
    try:
        resp = _chat(model=None, messages=[{"role": "system", "content": system}, {"role": "user", "content": text[:2000]}], max_tokens=150, temperature=0.0)
        content = resp["choices"][0]["message"]["content"].strip()
        content = content.replace("```json", "").replace("```", "").strip()
        result = json.loads(content)
        return {"score": int(result.get("score", 0)), "reason": result.get("reason", "No specific reason provided.")}
    except Exception as e:
        print(f"LLM Relevance check failed: {e}")
        return {"score": 0, "reason": f"Evaluation failed: {str(e)}"}


def assess_document_category(text: str) -> str:
    """Use the LLM to classify the document into a category (policy, claim form, manual, SOP, endorsement, other).
    Returns a short category string."""
    system = (
        "You are a document classifier. Read the provided document text and return ONLY a JSON object with a single field 'category'.\n"
        "Choose one of these categories when appropriate: 'Policy Document', 'Claim Form', 'Policy Manual', 'SOP', 'Endorsement', 'Customer Letter', 'Other'.\n"
        "Return minimal text like: {\"category\": \"Policy Document\"}"
    )
    try:
        resp = _chat(model=MISTRAL_MODEL, messages=[{"role": "system", "content": system}, {"role": "user", "content": text[:2000]}], max_tokens=60, temperature=0.0)
        content = resp["choices"][0]["message"]["content"].strip()
        content = content.replace("```json", "").replace("```", "").strip()
        result = json.loads(content)
        cat = result.get("category")
        if isinstance(cat, str):
            return cat
    except Exception as e:
        print(f"LLM Category extraction failed: {e}")
    return "Other"

def process_and_store_document(file_bytes: bytes, filename: str) -> dict:
    print(f"\n[INFO] Starting processing for document: {filename}")
    print(f"[INFO] File size: {len(file_bytes)} bytes")
    
    # 1. Extract Text (support PDF and images)
    print(f"[INFO] Extracting text from {filename}...")
    lower = filename.lower()
    text = ""
    if lower.endswith('.pdf'):
        text = extract_text_from_pdf(file_bytes)
    elif lower.endswith(('.jpg', '.jpeg', '.png')):
        text = extract_text_from_image(file_bytes)
    elif lower.endswith('.txt'):
        text = file_bytes.decode('utf-8', errors='ignore')
    else:
        # try PDF fallback
        text = extract_text_from_pdf(file_bytes)
        
    if text:
        import re
        # Hotfix for brochure PDF column-collapse issue mixing footnotes with IVF
        text = text.replace("Endless Sum Insured#\nCovers Medical Expenses", "Endless Sum Insured (Note: Available only if Sum Insured of Rs. 10 Lakhs and above is opted)\nCovers Medical Expenses")
        text = re.sub(r"#Available only if Sum Insured of Rs\. 10\s*Lakhs and above is opted\.", "", text)

        # Hotfix for Plan Ahead^ footnote
        text = text.replace("Plan Ahead^\nContinuity benefit", "Plan Ahead (Note: For spouse <= 35 yrs or up to 2 newborns within 120 days of marriage/birth; opt at start or first renewal only)\nContinuity benefit")
        text = re.sub(r"\^For spouse.*?(?:renewal only\.)", "", text, flags=re.DOTALL)

        # Hotfix for Maternity covers$ footnote
        text = text.replace("Maternity Expenses$\n", "Maternity Expenses (Note: Covers come in bundle, have to be purchased together)\n")
        text = text.replace("Newborn Baby Care$\n", "Newborn Baby Care (Note: Covers come in bundle, have to be purchased together)\n")
        text = text.replace("Child Vaccination$\n", "Child Vaccination (Note: Covers come in bundle, have to be purchased together)\n")
        text = re.sub(r"\$Covers come in bundle, have to be purchased together\.", "", text)
    if not text.strip():
        print("[ERROR] Could not extract any text from the document.")
        return {"success": False, "error": "Could not extract text from document."}
        
    print(f"[INFO] Successfully extracted {len(text)} characters of text.")

    # 1.5 Assess Category
    print("[INFO] Calling LLM to assess document CATEGORY...")
    category = assess_document_category(text)
    print(f"[INFO] LLM Category Assigned: '{category}'")

    # 1.6 Assess Relevance
    print("[INFO] Calling LLM to assess document RELEVANCE...")
    relevance_result = assess_document_relevance(text)
    relevance_score = relevance_result.get("score", 0)
    relevance_reason = relevance_result.get("reason", "")
    
    print(f"[INFO] LLM Relevance Score: {relevance_score}/100")
    print(f"[INFO] LLM Reasoning: {relevance_reason}")
    
    if relevance_score < RELEVANCE_THRESHOLD:
        print(f"[WARNING] Document REJECTED. Score {relevance_score} is below threshold {RELEVANCE_THRESHOLD}.")
        return {
            "success": False, 
            "error": f"Document rejected: Relevance score {relevance_score}/100 is below threshold ({RELEVANCE_THRESHOLD}). Reason: {relevance_reason}", 
            "relevance_score": relevance_score, 
            "category": category,
            "reason": relevance_reason
        }
        
    print("[INFO] Document ACCEPTED. Proceeding with Graph Extraction & Vector Store Embedding...")

    # ── Generate summary (used by both ArangoDB and ChromaDB) ────────────────
    summary = ""
    try:
        resp = _chat(
            model=MISTRAL_MODEL,
            messages=[
                {"role": "system", "content": "Summarize the following document in 2-3 short sentences focusing on the key intent and topics."},
                {"role": "user", "content": text[:3000]}
            ],
            max_tokens=150, temperature=0.0
        )
        summary = resp["choices"][0]["message"]["content"].strip()
        print(f"[INFO] Document summary generated.")
    except Exception as e:
        print(f"[WARNING] Summary generation failed: {e}")

    # ── STEP 2: ArangoDB (Knowledge Graph) — runs FIRST ──────────────────────
    print("[INFO] Calling LLM to extract entities and relationships for the Knowledge Graph...")
    kg_data = extract_kg_from_text(text)
    print(f"[INFO] Graph Extraction Complete. Found {len(kg_data.get('nodes', []))} nodes and {len(kg_data.get('edges', []))} edges.")

    nodes_inserted = 0
    edges_inserted = 0

    print("[INFO] Inserting graph data into ArangoDB...")
    if _db and kg_data:
        nodes_col = _db.collection("kb_nodes")
        edges_col = _db.collection("kb_edges")

        # Create a root document node
        doc_key = None
        try:
            doc_key = f"doc_{str(uuid.uuid4())}"
            doc_node = {"_key": doc_key, "id": doc_key, "type": "document", "file_name": filename, "summary": summary}
            if not nodes_col.has(doc_key):
                nodes_col.insert(doc_node)
                nodes_inserted += 1
        except Exception:
            doc_key = None

        # Insert entity nodes
        for node in kg_data.get("nodes", []):
            try:
                _key = str(node.get("id", "")).replace(" ", "_").replace("/", "_").replace("\\", "_")
                if not _key:
                    continue
                node["_key"] = _key
                if not nodes_col.has(_key):
                    nodes_col.insert(node)
                    nodes_inserted += 1
            except Exception:
                pass

        # Insert relationship edges
        for edge in kg_data.get("edges", []):
            try:
                from_key = str(edge.get("_from", "")).replace(" ", "_").replace("/", "_").replace("\\", "_")
                to_key = str(edge.get("_to", "")).replace(" ", "_").replace("/", "_").replace("\\", "_")
                if not from_key or not to_key:
                    continue
                edges_col.insert({
                    "_from": f"kb_nodes/{from_key}",
                    "_to": f"kb_nodes/{to_key}",
                    "label": edge.get("label", "related_to")
                })
                edges_inserted += 1
            except Exception:
                pass

        # Link document node → each entity
        if doc_key:
            for node in kg_data.get("nodes", []):
                try:
                    ent_key = str(node.get("id", "")).replace(" ", "_").replace("/", "_").replace("\\", "_")
                    if not ent_key:
                        continue
                    edges_col.insert({"_from": f"kb_nodes/{doc_key}", "_to": f"kb_nodes/{ent_key}", "label": "mentions"})
                    edges_inserted += 1
                except Exception:
                    pass

        print(f"[INFO] ArangoDB: Inserted {nodes_inserted} new nodes and {edges_inserted} new edges.")
    else:
        if not _db:
            print("[WARNING] ArangoDB connection not available. Graph data not stored.")

    # ── STEP 3: ChromaDB (Vector Store) — runs SECOND ────────────────────────
    print("[INFO] Chunking text into smaller segments...")
    chunks = chunk_text(text)
    print(f"[INFO] Created {len(chunks)} text chunks.")

    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [{"source": filename, "chunk_index": i, "summary": summary} for i in range(len(chunks))]

    print(f"[INFO] Adding {len(chunks)} chunks to ChromaDB vector store...")
    kb_collection.add(
        documents=chunks,
        ids=ids,
        metadatas=metadatas
    )
    print("[INFO] Successfully embedded and stored chunks in ChromaDB.")

    print(f"[INFO] Finished processing {filename} successfully!\n")
    return {
        "success": True,
        "chunks_embedded": len(chunks),
        "nodes_created": nodes_inserted,
        "edges_created": edges_inserted,
        "summary": summary,
        "relevance_score": relevance_score,
        "category": category
    }

def search_kb_documents(query: str, top_k: int = 5) -> list:
    """Semantic search in the company knowledge base."""
    try:
        if kb_collection.count() == 0:
            return []
        
        results = kb_collection.query(
            query_texts=[query],
            n_results=min(top_k, kb_collection.count())
        )
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        enriched = []
        for d, m in zip(docs, metas):
            src = m.get("source", "Company KB") if m else "Company KB"
            enriched.append(f"[Source: {src}]\n{d}")
        return enriched
    except Exception as e:
        print(f"KB search error: {e}")
        return []
