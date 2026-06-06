# api/controllers/document_controller.py
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from middleware.jwt_auth import verify_token
from utils.otp import is_user_verified
import os

router = APIRouter(prefix="/documents", tags=["Documents"])

# Ensure uploads directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
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
        from utils.rag_helper import ingest_document
        import time
        doc_id = int(time.time())
        user_id = int(token_data.get("sub"))
        chunks_stored = ingest_document(user_id, doc_id, file_location, file.filename)
    except Exception as e:
        print(f"Failed to ingest document into RAG: {e}")
        chunks_stored = 0
    
    return {
        "message": "File uploaded successfully",
        "filename": file.filename,
        "chunks_indexed": chunks_stored
    }
