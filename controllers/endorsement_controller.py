# api/controllers/endorsement_controller.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from database.db import execute_query
from middleware.jwt_auth import verify_token
from utils.common import write_audit_log

router = APIRouter(prefix="/endorsements", tags=["Endorsements"])

class EndorseRequest(BaseModel):
    policy_id: int
    update_type: str   # "address", "phone", "email", "nominee"
    new_value: str
    apply_to_all: bool = False

@router.post("")
def create_endorsement(body: EndorseRequest, token_data: dict = Depends(verify_token)):
    user_id = int(token_data["sub"])

    if body.apply_to_all:
        policies = execute_query(
            "SELECT id, policy_number FROM policies WHERE customer_id = %s AND status = 'active'",
            (user_id,), fetch="all"
        )
    else:
        pol = execute_query("SELECT id, policy_number FROM policies WHERE id = %s AND customer_id = %s", (body.policy_id, user_id), fetch="one")
        if not pol:
            raise HTTPException(status_code=404, detail="Policy not found")
        policies = [pol]

    if not policies:
        raise HTTPException(status_code=400, detail="No eligible policies found")

    # Get old value for audit
    old_value = None
    if body.update_type == "address":
        user = execute_query("SELECT address FROM users WHERE id = %s", (user_id,), fetch="one")
        old_value = user.get("address", "")
        execute_query("UPDATE users SET address = %s WHERE id = %s", (body.new_value, user_id), fetch="none")
    elif body.update_type in ("phone", "email"):
        user = execute_query("SELECT phone, email FROM users WHERE id = %s", (user_id,), fetch="one")
        old_value = user.get(body.update_type, "")
        execute_query(f"UPDATE users SET {body.update_type} = %s WHERE id = %s", (body.new_value, user_id), fetch="none")

    endorsement_ids = []
    for pol in policies:
        eid = execute_query(
            "INSERT INTO endorsements (policy_id, user_id, update_type, old_value, new_value, status) VALUES (%s,%s,%s,%s,%s,'approved')",
            (pol["id"], user_id, body.update_type, old_value, body.new_value), fetch="none"
        )
        endorsement_ids.append(eid)

    execute_query(
        "INSERT INTO notifications (user_id, title, message, type) VALUES (%s, %s, %s, 'update')",
        (user_id, "Endorsement Confirmed", f"{body.update_type.replace('_',' ').title()} updated successfully across {len(policies)} polic{'y' if len(policies)==1 else 'ies'}."),
        fetch="none"
    )
    write_audit_log(user_id, f"{body.update_type.upper()}_UPDATE", "endorsement", endorsement_ids[0] if endorsement_ids else None,
                    f"Changed {body.update_type} from '{old_value}' to '{body.new_value[:50]}' on {len(policies)} polic(ies)", severity="sensitive")

    return {"message": f"{body.update_type} updated on {len(policies)} policy/policies", "endorsement_ids": endorsement_ids}

@router.get("")
def list_endorsements(token_data: dict = Depends(verify_token)):
    user_id = int(token_data["sub"])
    rows = execute_query(
        """SELECT e.*, p.policy_number, p.policy_type FROM endorsements e
           JOIN policies p ON e.policy_id = p.id WHERE e.user_id = %s ORDER BY e.updated_at DESC""",
        (user_id,), fetch="all"
    )
    return {"endorsements": rows}
