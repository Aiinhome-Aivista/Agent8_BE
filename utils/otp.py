import random
import time

# Simple in-memory storage for OTPs. In production, use Redis or a database.
# Format: { "user@example.com": { "otp": "123456", "expires_at": 1690000000 } }
_otp_store = {}
# Verified users set to allow upload
_verified_users = set()

def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP of given length."""
    return "".join(str(random.randint(0, 9)) for _ in range(length))

def store_otp(email: str, otp: str, expires_in_sec: int = 300):
    """Store OTP for an email with an expiration time (default 5 mins)."""
    _otp_store[email] = {
        "otp": otp,
        "expires_at": time.time() + expires_in_sec
    }

def verify_otp(email: str, otp: str) -> bool:
    """Verify an OTP for an email. Returns True if valid and not expired."""
    record = _otp_store.get(email)
    if not record:
        return False
    
    if time.time() > record["expires_at"]:
        del _otp_store[email]
        return False
    
    if record["otp"] == otp:
        del _otp_store[email]
        _verified_users.add(email)
        return True
    
    return False

def is_user_verified(email: str) -> bool:
    """Check if the user has completed OTP verification."""
    return email in _verified_users

# --- Chat OTP Flow State ---
# Format: { "session_id": { "state": "AWAITING_CONSENT" | "AWAITING_CODE", "query": "original message" } }
_chat_otp_flow = {}

def set_chat_otp_state(session_id: str, state: str, query: str = None):
    """Set the state of the interactive chat OTP flow for a session."""
    if session_id not in _chat_otp_flow:
        _chat_otp_flow[session_id] = {}
    _chat_otp_flow[session_id]["state"] = state
    if query is not None:
        _chat_otp_flow[session_id]["query"] = query

def get_chat_otp_state(session_id: str):
    """Get the current OTP flow state for a session."""
    return _chat_otp_flow.get(session_id)

def clear_chat_otp_state(session_id: str):
    """Clear the OTP flow state for a session."""
    if session_id in _chat_otp_flow:
        del _chat_otp_flow[session_id]
