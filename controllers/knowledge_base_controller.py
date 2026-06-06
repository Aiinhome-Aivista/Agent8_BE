from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List
from fastapi.responses import JSONResponse
import os
import uuid

from utils.kb_helper import process_and_store_document
from middleware.jwt_auth import verify_token
from database.db import execute_query

router = APIRouter(prefix="/kb", tags=["Knowledge Base"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_document(file: List[UploadFile] = File(...), token_data: dict = Depends(verify_token)):
    """Upload one or more documents to the Knowledge Base. Processes each into ArangoDB and ChromaDB."""
    # FastAPI will pass a single UploadFile if one file is sent, or multiple as a list when multiple files are submitted with same field name.
    from typing import List

    # Normalize to list
    files = file if isinstance(file, list) else [file]

    results = []
    try:
        user_id = int(token_data.get("sub")) if token_data and token_data.get("sub") else None
    except Exception:
        user_id = None

    for f in files:
        try:
            lower = f.filename.lower()
            if not lower.endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                results.append({"filename": f.filename, "success": False, "error": "Invalid file type"})
                continue

            file_bytes = await f.read()
            if len(file_bytes) > 5 * 1024 * 1024:
                results.append({"filename": f.filename, "success": False, "error": "File too large (max 5 MB)"})
                continue

            # Save
            file_id = str(uuid.uuid4())
            safe_filename = f"{file_id}_{f.filename}"
            filepath = os.path.join(UPLOAD_DIR, safe_filename)
            with open(filepath, "wb") as fh:
                fh.write(file_bytes)

            # Process
            result = process_and_store_document(file_bytes, f.filename)

            # Will only insert into SQL if processing succeeded
            doc_id = None

            if not result.get("success"):
                results.append({
                    "filename": f.filename,
                    "success": False,
                    "error": result.get("error", "processing failed"),
                    "relevance_score": result.get("relevance_score")
                })
            else:
                # Insert valid document into SQL with category and relevance score
                try:
                    doc_id = execute_query(
                        "INSERT INTO uploaded_documents (user_id, policy_id, file_name, file_path, document_type, file_size, relevance_score, category) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                        (user_id, None, f.filename, filepath, 'knowledge_base', len(file_bytes), result.get("relevance_score"), result.get("category")), fetch="none"
                    )
                except Exception as e:
                    print(f"SQL Insert failed: {e}")
                    doc_id = None
                    
                results.append({
                    "filename": f.filename,
                    "success": True,
                    "relevance_score": result.get("relevance_score"),
                    "category": result.get("category"),
                    "metrics": {
                        "chunks_embedded": result.get("chunks_embedded", 0),
                        "nodes_created": result.get("nodes_created", 0),
                        "edges_created": result.get("edges_created", 0),
                        "relevance_score": result.get("relevance_score"),
                        "category": result.get("category")
                    },
                    "document_id": doc_id
                })
        except Exception as e:
            results.append({"filename": getattr(f, 'filename', 'unknown'), "success": False, "error": str(e)})

    return {"results": results}


@router.get("/list")
def list_kb_documents(token_data: dict = Depends(verify_token)):
    """Return knowledge base uploads for the authenticated user."""
    user_id = None
    try:
        user_id = int(token_data.get("sub")) if token_data and token_data.get("sub") else None
    except Exception:
        user_id = None

    try:
        if user_id:
            rows = execute_query("SELECT * FROM uploaded_documents WHERE user_id=%s AND document_type=%s ORDER BY uploaded_at DESC", (user_id, 'knowledge_base'), fetch="all")
        else:
            rows = execute_query("SELECT * FROM uploaded_documents WHERE document_type=%s ORDER BY uploaded_at DESC", ('knowledge_base',), fetch="all")
        return {"documents": rows}
    except Exception as e:
        return {"documents": []}
