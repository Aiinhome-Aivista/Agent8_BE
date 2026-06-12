# api/controllers/rag_controller.py
import os
import shutil
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from database.db import execute_query
from middleware.jwt_auth import verify_token
from utils.common import write_audit_log
from utils.rag_helper import ingest_document, search_documents, extract_text_from_file
from utils.llm_helper import answer_rag_question

router = APIRouter(prefix="/documents", tags=["Documents & RAG"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png", "text/plain"}

class RAGQuery(BaseModel):
    question: str
    policy_id: Optional[int] = None

@router.post("/upload")
async def upload_document(
    policy_id: Optional[int] = Form(None),
    document_type: str = Form("General"),
    file: UploadFile = File(...),
    token_data: dict = Depends(verify_token)
):
    user_id = int(token_data["sub"])
    email = token_data.get("email")

    if file.content_type not in ALLOWED_TYPES and not file.filename.endswith((".pdf", ".jpg", ".png", ".txt")):
        raise HTTPException(status_code=400, detail="File type not allowed. Use PDF, JPG, PNG, or TXT.")

    # Read and check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10 MB.")

    # Save to disk temporarily
    user_dir = os.path.join(UPLOAD_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    safe_name = f"{user_id}_{file.filename.replace(' ', '_')}"
    file_path = os.path.join(user_dir, safe_name)

    with open(file_path, "wb") as f:
        f.write(content)

    # Name Verification
    user = execute_query("SELECT name FROM users WHERE id = %s", (user_id,), fetch="one")
    if user and user.get("name"):
        user_name = user["name"]
        extracted_text = extract_text_from_file(file_path)
        if user_name.lower() not in extracted_text.lower():
            # Delete the file since it's rejected
            os.remove(file_path)
            raise HTTPException(status_code=400, detail=f"Your name ({user_name}) was not found in the document. Upload rejected.")
    else:
        extracted_text = None

    # Save record to DB
    doc_id = execute_query(
        "INSERT INTO uploaded_documents (user_id, policy_id, file_name, file_path, document_type, file_size) VALUES (%s,%s,%s,%s,%s,%s)",
        (user_id, policy_id, file.filename, file_path, document_type, len(content)), fetch="none"
    )

    # Policy Extraction Logic
    if document_type == "Policy Document" and extracted_text and extracted_text.strip():
        from utils.local_llm_helper import _chat
        import json
        system_prompt = "You are a data extraction AI. Extract the following policy details from the given text and return it strictly as a JSON object: policy_number (string), policy_type (string, e.g. Health Insurance, Motor Insurance), premium (number), coverage_amount (number), start_date (YYYY-MM-DD), expiry_date (YYYY-MM-DD), insurer (string), and coverage_details (a JSON object mapping any other specific fields found in the document to their values, e.g. 'Age': '27', 'Medical Condition': 'Hypertension', 'Nominee Name': 'Anindita Mitra', etc.)."
        try:
            resp = _chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Text:\n{extracted_text[:4000]}"}
                ],
                json_mode=True
            )
            policy_data = json.loads(resp["choices"][0]["message"]["content"])
            if policy_data.get("policy_number") and policy_data.get("coverage_amount"):
                from datetime import date, timedelta
                today = date.today()
                s_date = policy_data.get("start_date") or today.isoformat()
                e_date = policy_data.get("expiry_date") or (today + timedelta(days=365)).isoformat()
                
                execute_query(
                    """INSERT INTO policies (policy_number, customer_id, policy_type, insurer, premium, coverage_amount, start_date, expiry_date, status, policy_details)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'active', %s) ON DUPLICATE KEY UPDATE premium=VALUES(premium), coverage_amount=VALUES(coverage_amount)""",
                    (policy_data.get("policy_number"), user_id, policy_data.get("policy_type", "Health Insurance"), policy_data.get("insurer", "InsureAI"), policy_data.get("premium", 0), policy_data.get("coverage_amount"), s_date, e_date, json.dumps(policy_data)),
                    fetch="none"
                )
                print(f"Successfully extracted and inserted policy: {policy_data.get('policy_number')}")
        except Exception as e:
            print(f"Failed to parse LLM response or insert policy: {e}")

    # Ingest into ChromaDB (PDF/TXT only)
    chunks_stored = 0
    if file.filename.endswith((".pdf", ".txt")):
        try:
            chunks_stored = ingest_document(user_id, doc_id, file_path, file.filename, pre_extracted_text=extracted_text)
            if chunks_stored > 0:
                execute_query("UPDATE uploaded_documents SET is_processed=1 WHERE id=%s", (doc_id,), fetch="none")
        except Exception as e:
            print(f"RAG ingestion failed: {e}")

    write_audit_log(user_id, "DOCUMENT_UPLOAD", "document", doc_id,
                    f"Uploaded {file.filename} ({len(content)//1024} KB) — {chunks_stored} chunks indexed")

    return {
        "message": "Document uploaded successfully",
        "document_id": doc_id,
        "file_name": file.filename,
        "file_size": len(content),
        "chunks_indexed": chunks_stored,
        "rag_enabled": chunks_stored > 0
    }

@router.get("")
def list_documents(token_data: dict = Depends(verify_token)):
    user_id = int(token_data["sub"])
    rows = execute_query(
        """SELECT d.*, p.policy_number, p.policy_type FROM uploaded_documents d
           LEFT JOIN policies p ON d.policy_id = p.id WHERE d.user_id = %s ORDER BY d.uploaded_at DESC""",
        (user_id,), fetch="all"
    )
    return {"documents": rows, "total": len(rows)}

@router.post("/ask")
def ask_document(body: RAGQuery, token_data: dict = Depends(verify_token)):
    user_id = int(token_data["sub"])
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Check user has uploaded docs
    doc_count = execute_query("SELECT COUNT(*) as cnt FROM uploaded_documents WHERE user_id=%s AND is_processed=1", (user_id,), fetch="one")

    if doc_count["cnt"] == 0:
        return {
            "answer": "No processed documents found. Please upload your policy PDF documents first, then ask questions.",
            "sources": [],
            "question": body.question
        }

    # Semantic search
    chunks = search_documents(user_id, body.question)

    # Generate answer using RAG
    answer = answer_rag_question(body.question, chunks)

    write_audit_log(user_id, "RAG_QUERY", "document", None, f"Question: {body.question[:80]}")

    return {
        "answer": answer,
        "sources": chunks[:3],
        "question": body.question,
        "chunks_retrieved": len(chunks)
    }

@router.delete("/{doc_id}")
def delete_document(doc_id: int, token_data: dict = Depends(verify_token)):
    user_id = int(token_data["sub"])
    doc = execute_query("SELECT * FROM uploaded_documents WHERE id=%s AND user_id=%s", (doc_id, user_id), fetch="one")
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove file from disk
    try:
        if os.path.exists(doc["file_path"]):
            os.remove(doc["file_path"])
    except Exception:
        pass

    execute_query("DELETE FROM uploaded_documents WHERE id=%s", (doc_id,), fetch="none")
    write_audit_log(user_id, "DOCUMENT_DELETED", "document", doc_id, f"Deleted {doc['file_name']}")
    return {"message": "Document deleted"}
