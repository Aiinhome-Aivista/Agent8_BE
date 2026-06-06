# api/controllers/notification_controller.py
from fastapi import APIRouter, Depends
from database.db import execute_query
from middleware.jwt_auth import verify_token

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("")
def list_notifications(token_data: dict = Depends(verify_token)):
    user_id = int(token_data["sub"])
    rows = execute_query(
        "SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC LIMIT 50",
        (user_id,), fetch="all"
    )
    unread = sum(1 for r in rows if r["status"] == "unread")
    return {"notifications": rows, "unread_count": unread}

@router.patch("/{notif_id}/read")
def mark_read(notif_id: int, token_data: dict = Depends(verify_token)):
    user_id = int(token_data["sub"])
    execute_query("UPDATE notifications SET status='read' WHERE id=%s AND user_id=%s", (notif_id, user_id), fetch="none")
    return {"message": "Marked as read"}

@router.patch("/read-all")
def mark_all_read(token_data: dict = Depends(verify_token)):
    user_id = int(token_data["sub"])
    execute_query("UPDATE notifications SET status='read' WHERE user_id=%s", (user_id,), fetch="none")
    return {"message": "All notifications marked as read"}
