# api/controllers/document_controller.py
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from middleware.jwt_auth import verify_token
from utils.otp import is_user_verified
from database.db import execute_query
import os
import json

router = APIRouter(prefix="/documents", tags=["Documents"])

# Ensure uploads directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(None),
    token_data: dict = Depends(verify_token)
):
    """Upload a document. User must have completed OTP verification."""
    email = token_data.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token structure")
    
    # Check OTP verification status
    if not is_user_verified(email):
        raise HTTPException(status_code=403, detail="Document upload requires OTP verification.")
    
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(file_location, "wb+") as file_object:
            file_object.write(await file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")
    
    # Process and store the document in ChromaDB for AI Retrieval (RAG)
    try:
        from utils.rag_helper import ingest_document, extract_text_from_file
        from utils.local_llm_helper import _chat
        import time
        
        user_id = int(token_data.get("sub"))
        doc_id = int(time.time())
        
        # 1. Extract text from file
        extracted_text = extract_text_from_file(file_location)
        
        # 2. Extract policy details if it's a policy document
        if document_type == "Policy Document" and extracted_text.strip():
            system_prompt = "You are a data extraction AI. Extract the following policy details from the given text and return it strictly as a JSON object: policy_number (string), policy_type (string, e.g. Health Insurance, Motor Insurance), premium (number), coverage_amount (number), start_date (YYYY-MM-DD), expiry_date (YYYY-MM-DD), insurer (string)."
            resp = _chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Text:\n{extracted_text[:4000]}"}
                ],
                json_mode=True
            )
            
            try:
                content = resp["choices"][0]["message"]["content"]
                policy_data = json.loads(content)
                
                # Insert into DB if required fields are present
                if policy_data.get("policy_number") and policy_data.get("coverage_amount"):
                    # Use defaults if some dates are missing
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
                
        # 3. Ingest into RAG using the already extracted text
        chunks_stored = ingest_document(user_id, doc_id, file_location, file.filename, pre_extracted_text=extracted_text)
    except Exception as e:
        print(f"Failed to ingest document into RAG: {e}")
        chunks_stored = 0
    
    return {
        "message": "File uploaded successfully",
        "filename": file.filename,
        "chunks_indexed": chunks_stored
    }
