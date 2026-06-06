# api/controllers/auth_controller.py
# Handles: POST /register, POST /login, GET /me

import bcrypt
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr
from database.db import execute_query
from middleware.jwt_auth import create_token, verify_token
from utils.common import write_audit_log

router = APIRouter(prefix="/auth", tags=["Auth"])

# --- Request models ---
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str
    role: str = "customer"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SendOtpRequest(BaseModel):
    email: EmailStr

class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str

from utils.email import send_email
from utils.otp import generate_otp, store_otp, verify_otp, is_user_verified

# --- Routes ---

@router.post("/register")
def register(body: RegisterRequest):
    """Register a new user. Only 'customer' role allowed via self-registration."""
    # Check email uniqueness
    existing = execute_query("SELECT id FROM users WHERE email = %s", (body.email,), fetch="one")
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Only customers can self-register
    role = "customer" if body.role not in ["customer"] else body.role

    # Hash password
    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()

    user_id = execute_query(
        "INSERT INTO users (name, email, phone, password, role) VALUES (%s, %s, %s, %s, %s)",
        (body.name, body.email, body.phone, hashed, role),
        fetch="none"
    )

    write_audit_log(user_id, "USER_REGISTERED", "auth", user_id, f"New customer: {body.email}")

    token = create_token(user_id, body.email, role)
    return {"message": "Registration successful", "token": token, "role": role, "user_id": user_id, "name": body.name}


@router.post("/login")
def login(body: LoginRequest, request: Request):
    """Authenticate user and return JWT token."""
    user = execute_query(
        "SELECT id, name, email, password, role, phone, address, is_active FROM users WHERE email = %s",
        (body.email,), fetch="one"
    )

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    # Verify password
    if not bcrypt.checkpw(body.password.encode(), user["password"].encode()):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    ip = request.client.host if request.client else "unknown"
    write_audit_log(user["id"], "LOGIN", "auth", user["id"], f"Login from {ip}", severity="normal", ip_address=ip)

    token = create_token(user["id"], user["email"], user["role"])

    return {
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "phone": user["phone"],
            "address": user["address"],
        }
    }


@router.post("/send-otp")
def send_otp(body: SendOtpRequest):
    """Generate and send an OTP to the user's email."""
    # Check if user exists
    user = execute_query("SELECT id FROM users WHERE email = %s", (body.email,), fetch="one")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    otp = generate_otp()
    store_otp(body.email, otp)
    
    # Send email
    subject = "Your InsureAI Pro Verification Code"
    msg = f"Your verification code is: {otp}\n\nThis code will expire in 5 minutes."
    send_email(body.email, subject, msg)
    
    return {"message": "OTP sent successfully"}

@router.post("/verify-otp")
def verify_otp_route(body: VerifyOtpRequest):
    """Verify the OTP sent to the user."""
    is_valid = verify_otp(body.email, body.otp)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    return {"message": "OTP verified successfully"}

@router.get("/me")
def get_me(token_data: dict = Depends(verify_token)):
    """Return current user profile from token."""
    user_id = int(token_data["sub"])
    user = execute_query(
        "SELECT id, name, email, role, phone, address, created_at FROM users WHERE id = %s",
        (user_id,), fetch="one"
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
