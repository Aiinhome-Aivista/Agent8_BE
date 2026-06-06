# api/utils/common.py
# Shared helpers: audit logging, guardrail checking, ticket ID generation

import re
import random
import string
from database.db import execute_query

# Keywords that trigger guardrail violations
GUARDRAIL_PATTERNS = {
    "PII_EXTRACTION": ["pan card number", "aadhar number", "bank account", "cvv", "full card number", "ifsc of others"],
    "ABUSIVE_LANGUAGE": ["idiot", "stupid", "fool", "moron", "bastard", "kill", "threat"],
    "PROMPT_INJECTION": ["ignore previous", "ignore all instructions", "pretend you are", "jailbreak", "act as root", "disregard"],
    "SENSITIVE_DATA_REQUEST": ["all customer data", "all user emails", "dump database", "all policies"],
}

def check_guardrails(message: str, user_id: int, session_id: str = None) -> dict:
    """
    Check message against guardrail patterns.
    Logs violation and returns {"violated": bool, "violation_type": str}
    """
    lower = message.lower()
    for violation_type, patterns in GUARDRAIL_PATTERNS.items():
        for pattern in patterns:
            if pattern in lower:
                # Log the violation
                execute_query(
                    "INSERT INTO guardrail_logs (user_id, session_id, violation_type, message, severity) VALUES (%s, %s, %s, %s, %s)",
                    (user_id, session_id, violation_type, message[:500], "high"),
                    fetch="none"
                )
                write_audit_log(
                    user_id=user_id,
                    action="GUARDRAIL_VIOLATION",
                    entity_type="chat",
                    details=f"Violation type: {violation_type} — Message: {message[:100]}",
                    severity="high"
                )
                return {"violated": True, "violation_type": violation_type}
    return {"violated": False, "violation_type": None}

def write_audit_log(
    user_id: int,
    action: str,
    entity_type: str = None,
    entity_id: int = None,
    details: str = None,
    severity: str = "normal",
    ip_address: str = None
):
    """Insert a row into audit_logs. Call this from any controller."""
    execute_query(
        """INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address, severity)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (user_id, action, entity_type, entity_id, details, ip_address, severity),
        fetch="none"
    )

def generate_ticket_id() -> str:
    """Generate ESC-YYYYMMDD-XXXX style ticket IDs."""
    from datetime import date
    today = date.today().strftime("%Y%m%d")
    suffix = "".join(random.choices(string.digits, k=4))
    return f"ESC-{today}-{suffix}"

def generate_transaction_id() -> str:
    """Generate a fake but realistic UPI transaction ID."""
    return "TXN" + "".join(random.choices(string.digits, k=12))

def paginate(query: str, params: tuple, page: int, page_size: int) -> tuple:
    """Append LIMIT/OFFSET to a query for pagination. Returns (query, params)."""
    offset = (page - 1) * page_size
    return query + " LIMIT %s OFFSET %s", params + (page_size, offset)
