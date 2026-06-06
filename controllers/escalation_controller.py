# api/controllers/escalation_controller.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from database.db import execute_query
from middleware.jwt_auth import verify_token, require_role
from utils.common import write_audit_log, generate_ticket_id

router = APIRouter(prefix="/escalations", tags=["Escalations"])

class EscalationCreate(BaseModel):
    policy_id: Optional[int] = None
    issue: str
    category: str = "General"
    priority: str = "medium"

class EscalationUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[int] = None
    resolution_notes: Optional[str] = None
    note: Optional[str] = None  # CSR note

from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
import os
import uuid

@router.post("")
async def create_escalation(
    issue: str = Form(...),
    category: str = Form("General"),
    priority: str = Form("medium"),
    policy_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    token_data: dict = Depends(verify_token)
):
    user_id = int(token_data["sub"])
    if len(issue.strip()) < 10:
        raise HTTPException(status_code=400, detail="Issue description must be at least 10 characters")

    ticket_id = generate_ticket_id()
    
    attachment_path = None
    if file:
        lower = file.filename.lower()
        if not lower.endswith(('.png', '.jpg', '.jpeg', '.pdf')):
            raise HTTPException(status_code=400, detail="Only PNG, JPG, or PDF files are allowed for attachments.")
        
        UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_id = str(uuid.uuid4())
        safe_filename = f"ticket_{file_id}_{file.filename}"
        filepath = os.path.join(UPLOAD_DIR, safe_filename)
        
        file_bytes = await file.read()
        with open(filepath, "wb") as fh:
            fh.write(file_bytes)
        attachment_path = f"uploads/{safe_filename}"

    # Auto-assign to first available CSR
    csr = execute_query("SELECT id FROM users WHERE role = 'csr' AND is_active = 1 LIMIT 1", fetch="one")
    assigned = csr["id"] if csr else None

    # Parse policy_id as int if provided
    pid = int(policy_id) if policy_id and policy_id != "null" else None

    esc_id = execute_query(
        """INSERT INTO escalations (ticket_id, user_id, policy_id, issue, category, priority, status, assigned_to, attachment_path)
           VALUES (%s, %s, %s, %s, %s, %s, 'open', %s, %s)""",
        (ticket_id, user_id, pid, issue, category, priority, assigned, attachment_path),
        fetch="none"
    )
    execute_query(
        "INSERT INTO notifications (user_id, title, message, type) VALUES (%s, %s, %s, 'escalation')",
        (user_id, "Support Ticket Created", f"Your ticket {ticket_id} has been created. Expected response within 2 hours."),
        fetch="none"
    )
    
        # Notify the assigned CSR
    if assigned:
        execute_query(
            "INSERT INTO notifications (user_id, title, message, type) VALUES (%s, %s, %s, 'escalation')",
            (assigned, "New Ticket Assigned", f"Ticket {ticket_id} (Category: {category}) has been assigned to you."),
            fetch="none"
        )
        
        # Send an email to the CSR
        csr_email = execute_query("SELECT email FROM users WHERE id = %s", (assigned,), fetch="one")
        if csr_email:
            subject = f"New Ticket Assigned - {ticket_id}"
            attachment_text = f"\nAttachment: http://localhost:8000/api/{attachment_path.replace(chr(92), '/')}" if attachment_path else ""
            body_text = f"A new ticket has been assigned to you.\n\nCategory: {category}\nIssue: {issue}\nPriority: {priority}\n{attachment_text}\n"
            
            from utils.email import send_email
            send_email(csr_email['email'], subject, body_text)

    write_audit_log(user_id, "ESCALATION_CREATED", "escalation", esc_id, f"Ticket {ticket_id}: {issue[:80]}")
    return {"message": "Ticket created", "ticket_id": ticket_id, "escalation_id": esc_id, "assigned_to": assigned}

@router.get("")
def list_escalations(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    token_data: dict = Depends(verify_token)
):
    user_id = int(token_data["sub"])
    role = token_data["role"]

    where = []
    params = []

    if role == "customer":
        where.append("e.user_id = %s")
        params.append(user_id)
    elif role == "csr":
        where.append("(e.assigned_to = %s OR e.assigned_to IS NULL)")
        params.append(user_id)

    if status:
        where.append("e.status = %s")
        params.append(status)
    if priority:
        where.append("e.priority = %s")
        params.append(priority)

    where_clause = "WHERE " + " AND ".join(where) if where else ""

    rows = execute_query(
        f"""SELECT e.*, u.name as customer_name, u.email as customer_email, u.phone as customer_phone,
                   a.name as assigned_csr_name, p.policy_number, p.policy_type
            FROM escalations e
            JOIN users u ON e.user_id = u.id
            LEFT JOIN users a ON e.assigned_to = a.id
            LEFT JOIN policies p ON e.policy_id = p.id
            {where_clause}
            ORDER BY FIELD(e.priority,'critical','high','medium','low'), e.created_at DESC""",
        tuple(params), fetch="all"
    )
    return {"escalations": rows, "total": len(rows)}

@router.get("/{esc_id}")
def get_escalation(esc_id: int, token_data: dict = Depends(verify_token)):
    row = execute_query(
        """SELECT e.*, u.name as customer_name, u.email as customer_email, u.phone as customer_phone,
                  a.name as assigned_csr_name
           FROM escalations e JOIN users u ON e.user_id = u.id LEFT JOIN users a ON e.assigned_to = a.id
           WHERE e.id = %s""",
        (esc_id,), fetch="one"
    )
    if not row:
        raise HTTPException(status_code=404, detail="Escalation not found")
    # Get CSR notes
    notes = execute_query(
        "SELECT cn.*, u.name as csr_name FROM csr_notes cn JOIN users u ON cn.csr_id = u.id WHERE cn.escalation_id = %s ORDER BY cn.created_at",
        (esc_id,), fetch="all"
    )
    row["notes"] = notes
    return row

@router.patch("/{esc_id}")
def update_escalation(esc_id: int, body: EscalationUpdate, token_data: dict = Depends(verify_token)):
    user_id = int(token_data["sub"])
    role = token_data["role"]
    if role not in ("csr", "supervisor", "compliance"):
        raise HTTPException(status_code=403, detail="Only CSR/Supervisor can update tickets")

    esc = execute_query("SELECT * FROM escalations WHERE id = %s", (esc_id,), fetch="one")
    if not esc:
        raise HTTPException(status_code=404, detail="Escalation not found")

    updates, params = [], []
    if body.status:
        updates.append("status = %s"); params.append(body.status)
    if body.assigned_to is not None:
        updates.append("assigned_to = %s"); params.append(body.assigned_to)
    if body.resolution_notes:
        updates.append("resolution_notes = %s"); params.append(body.resolution_notes)
    if updates:
        params.append(esc_id)
        execute_query(f"UPDATE escalations SET {', '.join(updates)} WHERE id = %s", tuple(params), fetch="none")

    if body.note:
        execute_query(
            "INSERT INTO csr_notes (escalation_id, csr_id, note) VALUES (%s, %s, %s)",
            (esc_id, user_id, body.note), fetch="none"
        )

    write_audit_log(user_id, "ESCALATION_UPDATED", "escalation", esc_id,
                    f"Ticket {esc['ticket_id']} updated: status={body.status}, note={str(body.note)[:50] if body.note else None}")
    return {"message": "Escalation updated"}
