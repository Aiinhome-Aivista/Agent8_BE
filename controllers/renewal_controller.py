# api/controllers/renewal_controller.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from database.db import execute_query
from middleware.jwt_auth import verify_token
from utils.common import write_audit_log, generate_transaction_id
from datetime import date, timedelta

router = APIRouter(prefix="/renewals", tags=["Renewals"])

class RenewRequest(BaseModel):
    policy_id: int
    payment_method: str = "UPI"

@router.post("")
def renew_policy(body: RenewRequest, token_data: dict = Depends(verify_token)):
    user_id = int(token_data["sub"])
    policy = execute_query(
        "SELECT * FROM policies WHERE id = %s AND customer_id = %s",
        (body.policy_id, user_id), fetch="one"
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found or access denied")
    if policy["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot renew a cancelled policy")

    prev_expiry = policy["expiry_date"]
    new_expiry = date.today().replace(year=date.today().year + 1) if policy["status"] == "expired" else \
                 (prev_expiry if isinstance(prev_expiry, date) else date.fromisoformat(str(prev_expiry))).replace(
                     year=(prev_expiry if isinstance(prev_expiry, date) else date.fromisoformat(str(prev_expiry))).year + 1
                 )

    txn_id = generate_transaction_id()
    renewal_id = execute_query(
        """INSERT INTO renewals (policy_id, user_id, previous_expiry, new_expiry, amount, payment_method, transaction_id, payment_status)
           VALUES (%s, %s, %s, %s, %s, %s, %s, 'completed')""",
        (body.policy_id, user_id, prev_expiry, new_expiry, policy["premium"], body.payment_method, txn_id),
        fetch="none"
    )
    execute_query(
        "UPDATE policies SET expiry_date = %s, status = 'active' WHERE id = %s",
        (new_expiry, body.policy_id), fetch="none"
    )
    execute_query(
        "INSERT INTO notifications (user_id, title, message, type) VALUES (%s, %s, %s, 'payment')",
        (user_id, "Renewal Successful", f"Policy {policy['policy_number']} renewed. ₹{policy['premium']:,.0f} paid via {body.payment_method}. New expiry: {new_expiry}. TXN: {txn_id}"),
        fetch="none"
    )
    write_audit_log(user_id, "POLICY_RENEWAL", "policy", body.policy_id,
                    f"Renewed {policy['policy_number']} — ₹{policy['premium']:,.0f} via {body.payment_method}. TXN: {txn_id}", severity="sensitive")
    return {
        "message": "Policy renewed successfully",
        "renewal_id": renewal_id,
        "policy_number": policy["policy_number"],
        "new_expiry": str(new_expiry),
        "amount": float(policy["premium"]),
        "transaction_id": txn_id,
        "payment_method": body.payment_method
    }

@router.get("")
def list_renewals(token_data: dict = Depends(verify_token)):
    user_id = int(token_data["sub"])
    rows = execute_query(
        """SELECT r.*, p.policy_number, p.policy_type FROM renewals r
           JOIN policies p ON r.policy_id = p.id WHERE r.user_id = %s ORDER BY r.renewed_at DESC""",
        (user_id,), fetch="all"
    )
    return {"renewals": rows}
