# api/controllers/chat_controller.py
# Handles: POST /chat, GET /chat/history, DELETE /chat/history

import uuid, json, re
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from database.db import execute_query
from middleware.jwt_auth import verify_token
from utils.llm_helper import answer_rag_question, generate_chat_response, detect_intent
from utils.rag_helper import search_documents
from utils.common import check_guardrails, write_audit_log
from utils.otp import (
    is_user_verified, generate_otp, store_otp, verify_otp,
    set_chat_otp_state, get_chat_otp_state, clear_chat_otp_state
)
from utils.email import send_email


def _clean_response(text: str) -> str:
    """Strip JSON wrappers the LLM sometimes adds, returning plain text.
    Handles:
      {"assistant": {"message": "..."}}
      {"response": "..."}  /  {"message": "..."}
      "✅ prefix text\n\n{json}"  — prefix followed by JSON block
    Also removes stray backtick fences and empty objects {}.
    """
    if not text:
        return text
    stripped = text.strip()
    # Remove markdown code fences
    stripped = re.sub(r'^```[\w]*\n?', '', stripped)
    stripped = re.sub(r'```$', '', stripped).strip()

    def _extract_from_obj(obj: dict) -> str | None:
        """Pull a string message out of a parsed JSON object."""
        if isinstance(obj.get('assistant'), dict):
            return obj['assistant'].get('message', '').strip() or None
        for key in ('message', 'response', 'reply', 'content', 'answer'):
            if isinstance(obj.get(key), str) and obj[key].strip():
                return obj[key].strip()
        return None

    # Case 1: entire response is JSON
    if stripped.startswith('{'):
        try:
            obj = json.loads(stripped)
            msg = _extract_from_obj(obj)
            if msg:
                return msg
            # Empty object {} → return empty (caller will handle)
            return ''
        except Exception:
            # If it's heavily malformed or just a stray bracket, drop it
            if len(stripped) < 10 or '}' not in stripped:
                return ''

    # Case 2: human-readable prefix + "\n\n{json}" (e.g. after OTP verification)
    if '\n\n' in stripped:
        prefix, _, rest = stripped.partition('\n\n')
        rest = rest.strip()
        if rest.startswith('{'):
            try:
                obj = json.loads(rest)
                msg = _extract_from_obj(obj)
                if msg:
                    return prefix.strip() + '\n\n' + msg
                # JSON was empty/useless — just keep the prefix
                return prefix.strip()
            except Exception:
                # Malformed JSON after prefix → drop the broken json part
                if len(rest) < 10 or '}' not in rest:
                    return prefix.strip()

    # Fallback to remove trailing stray brackets
    if stripped.endswith('\n\n{'):
        stripped = stripped[:-3].strip()
    elif stripped == '{':
        stripped = ''

    return stripped


router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatHistoryItem(BaseModel):
    role: str
    content: str

@router.post("")
def chat(body: ChatRequest, token_data: dict = Depends(verify_token)):
    """
    Main AI chat endpoint.
    1. OTP verification flow (conversational, not a hard 403)
    2. Guardrail check
    3. Intent detection
    4. Build customer context from DB
    5. Generate AI response
    6. Save to chat_history
    7. Return response + intent metadata
    """
    user_id = int(token_data["sub"])
    email = token_data.get("email")
    session_id = body.session_id or str(uuid.uuid4())
    message = body.message.strip()
    _otp_just_verified = False
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # --- Conversational OTP verification flow ---
    if not is_user_verified(email):
        otp_state = get_chat_otp_state(session_id)

        # STATE: No verification attempt yet — save query, ask for consent
        if otp_state is None:
            set_chat_otp_state(session_id, state="AWAITING_CONSENT", query=message)
            prompt_msg = (
                "🔒 To assist you securely, I need to verify your identity first.\n\n"
                "Shall I send a One-Time Password (OTP) to your registered email address? "
                "Please reply **yes** to proceed."
            )
            execute_query(
                "INSERT INTO chat_history (user_id, session_id, user_message, ai_response, detected_intent, confidence_score) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (user_id, session_id, message, prompt_msg, "otp_consent_prompt", 1.0), fetch="none"
            )
            return {
                "response": prompt_msg,
                "session_id": session_id,
                "intent": "otp_consent_prompt",
                "confidence": 1.0,
                "guardrail_violated": False,
                "otp_required": True,
            }

        # STATE: Waiting for consent — check if user said yes
        if otp_state["state"] == "AWAITING_CONSENT":
            if message.strip().lower() in ["yes", "hya", "y", "ok", "okay", "sure", "ha"]:
                # Generate and send OTP
                otp = generate_otp()
                store_otp(email, otp)
                send_email(
                    email,
                    "Your InsureAI Pro Verification Code",
                    f"Your verification code is: {otp}\n\nThis code will expire in 5 minutes.\nDo not share this code with anyone."
                )
                set_chat_otp_state(session_id, state="AWAITING_CODE")
                sent_msg = (
                    f"✅ An OTP has been sent to your registered email address.\n\n"
                    f"Please enter the 6-digit code here to verify your identity."
                )
                execute_query(
                    "INSERT INTO chat_history (user_id, session_id, user_message, ai_response, detected_intent, confidence_score) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (user_id, session_id, message, sent_msg, "otp_sent", 1.0), fetch="none"
                )
                return {
                    "response": sent_msg,
                    "session_id": session_id,
                    "intent": "otp_sent",
                    "confidence": 1.0,
                    "guardrail_violated": False,
                    "otp_required": True,
                }
            else:
                # User said something other than yes
                decline_msg = (
                    "I understand. To use the AI Assistant, identity verification is required for your security. "
                    "Whenever you're ready, just send your question again and I'll prompt you to verify."
                )
                clear_chat_otp_state(session_id)
                execute_query(
                    "INSERT INTO chat_history (user_id, session_id, user_message, ai_response, detected_intent, confidence_score) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (user_id, session_id, message, decline_msg, "otp_declined", 1.0), fetch="none"
                )
                return {
                    "response": decline_msg,
                    "session_id": session_id,
                    "intent": "otp_declined",
                    "confidence": 1.0,
                    "guardrail_violated": False,
                    "otp_required": True,
                }

        # STATE: Waiting for OTP code
        if otp_state["state"] == "AWAITING_CODE":
            entered_code = message.strip()
            if verify_otp(email, entered_code):
                # Successful verification — retrieve original query and continue
                original_query = otp_state.get("query", message)
                clear_chat_otp_state(session_id)
                message = original_query   # process the user's original question below
                # Let flow continue to normal chat logic below
                # We'll add a prefix to the final response
                _otp_just_verified = True
            else:
                # Wrong or expired OTP
                invalid_msg = (
                    "❌ That code is incorrect or has expired. "
                    "Please check your email and try again, or start over by sending your question again."
                )
                execute_query(
                    "INSERT INTO chat_history (user_id, session_id, user_message, ai_response, detected_intent, confidence_score) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (user_id, session_id, message, invalid_msg, "otp_invalid", 1.0), fetch="none"
                )
                return {
                    "response": invalid_msg,
                    "session_id": session_id,
                    "intent": "otp_invalid",
                    "confidence": 1.0,
                    "guardrail_violated": False,
                    "otp_required": True,
                }
        else:
            _otp_just_verified = False
    else:
        _otp_just_verified = False

    # --- Guardrail check ---
    guard = check_guardrails(message, user_id, session_id)
    if guard["violated"]:
        blocked_msg = (
            "I'm sorry, but I'm unable to process that request. "
            "Please ensure your query complies with our platform guidelines. "
            "If you need help, please contact our support team."
        )
        execute_query(
            "INSERT INTO chat_history (user_id, session_id, user_message, ai_response, detected_intent, confidence_score) VALUES (%s,%s,%s,%s,%s,%s)",
            (user_id, session_id, message, blocked_msg, "guardrail_blocked", 1.0), fetch="none"
        )
        return {
            "response": blocked_msg,
            "session_id": session_id,
            "intent": "blocked",
            "confidence": 1.0,
            "guardrail_violated": True,
            "violation_type": guard["violation_type"]
        }

    # --- Delegate to Supervisor Agent ---
    from agents.supervisor.supervisor_agent import SupervisorAgent
    supervisor = SupervisorAgent()
    input_data = {
        "user_input": message,
        "user_id": user_id,
        "session_id": session_id
    }
    
    # Provide a default policy_id if policies exist (useful for RenewalAgent/PolicyAgent)
    if policies:
        input_data["policy_id"] = policies[0]["policy_number"]
        
    supervisor_result = supervisor.run(input_data)
    
    ai_response = supervisor_result.get("response", "Processed.")
    intent = supervisor_result.get("intent", "faq")
    confidence = 1.0

    # Prepend verification success message if OTP was just verified
    if _otp_just_verified:
        if not ai_response.strip():
            ai_response = "✅ **Identity verified successfully!**\n\nHow can I help you today? You can ask me about:\n• Your active policies and coverage details\n• Premium amounts and renewal dates\n• Downloading your policy documents\n• Raising a support ticket for complaints"
        else:
            ai_response = "✅ **Identity verified successfully!**\n\n" + ai_response

    # --- Persist to DB ---
    execute_query(
        """INSERT INTO chat_history 
           (user_id, session_id, user_message, ai_response, detected_intent, confidence_score, workflow_triggered)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (user_id, session_id, message, ai_response, intent, confidence, intent),
        fetch="none"
    )

    write_audit_log(
        user_id, "CHAT_MESSAGE", "chat", None,
        f"Intent: {intent} ({confidence:.0%}) | Message: {message[:80]}"
    )

    return {
        "response": ai_response,
        "session_id": session_id,
        "intent": intent,
        "confidence": confidence,
        "guardrail_violated": False,
        "worker_used": supervisor_result.get("worker_used", "UnknownAgent")
    }


@router.get("/history")
def get_chat_history(
    page: int = 1,
    page_size: int = 50,
    session_id: Optional[str] = None,
    token_data: dict = Depends(verify_token)
):
    """Return paginated chat history for the current user."""
    user_id = int(token_data["sub"])
    offset = (page - 1) * page_size

    if session_id:
        rows = execute_query(
            "SELECT id, session_id, user_message, ai_response, detected_intent, confidence_score, created_at FROM chat_history WHERE user_id = %s AND session_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (user_id, session_id, page_size, offset), fetch="all"
        )
    else:
        rows = execute_query(
            "SELECT id, session_id, user_message, ai_response, detected_intent, confidence_score, created_at FROM chat_history WHERE user_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (user_id, page_size, offset), fetch="all"
        )

    total = execute_query("SELECT COUNT(*) as cnt FROM chat_history WHERE user_id = %s", (user_id,), fetch="one")
    return {"history": rows, "total": total["cnt"], "page": page, "page_size": page_size}


@router.get("/sessions")
def get_sessions(token_data: dict = Depends(verify_token)):
    """Return distinct chat sessions for the current user, with title and preview."""
    user_id = int(token_data["sub"])
    sessions = execute_query(
        """SELECT session_id,
              MIN(created_at) as started_at,
              MAX(created_at) as last_at,
              COUNT(*) as message_count
           FROM chat_history WHERE user_id = %s
           GROUP BY session_id ORDER BY last_at DESC LIMIT 30""",
        (user_id,), fetch="all"
    )
    # Enrich each session with title (first user message) and preview (last AI reply)
    enriched = []
    for s in sessions:
        first_msg = execute_query(
            "SELECT user_message, detected_intent FROM chat_history WHERE user_id=%s AND session_id=%s ORDER BY created_at ASC LIMIT 1",
            (user_id, s["session_id"]), fetch="one"
        )
        last_msg = execute_query(
            "SELECT ai_response FROM chat_history WHERE user_id=%s AND session_id=%s ORDER BY created_at DESC LIMIT 1",
            (user_id, s["session_id"]), fetch="one"
        )
        title = (first_msg or {}).get("user_message", "Chat session")
        title = title[:60] + ("…" if len(title) > 60 else "")
        intent = (first_msg or {}).get("detected_intent") or "faq"
        preview_raw = (last_msg or {}).get("ai_response", "")
        # Clean JSON wrapper if present
        import json as _j, re as _re
        p = preview_raw.strip()
        p = _re.sub(r'^```[\w]*\n?', '', p); p = _re.sub(r'```$', '', p).strip()
        if p.startswith('{'):
            try:
                obj = _j.loads(p)
                if isinstance(obj.get('assistant'), dict): p = obj['assistant'].get('message', p)
                else:
                    for k in ('message','response','reply','content','answer'):
                        if isinstance(obj.get(k), str): p = obj[k]; break
            except: pass
        preview = p[:100] + ("…" if len(p) > 100 else "")
        enriched.append({**s, "title": title, "intent": intent, "preview": preview})
    return {"sessions": enriched}


@router.get("/sessions/customer/{customer_user_id}")
def get_customer_sessions_csr(customer_user_id: int, token_data: dict = Depends(verify_token)):
    """CSR-only: view sessions for an assigned customer."""
    if token_data.get("role") not in ("csr", "supervisor", "compliance"):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="CSR access only")
    csr_id = int(token_data["sub"])
    # Verify this CSR has an escalation linked to the customer
    linked = execute_query(
        "SELECT id FROM escalations WHERE assigned_to=%s AND user_id=%s LIMIT 1",
        (csr_id, customer_user_id), fetch="one"
    )
    if not linked:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not assigned to this customer")
    sessions = execute_query(
        """SELECT session_id, MIN(created_at) as started_at, MAX(created_at) as last_at, COUNT(*) as message_count
           FROM chat_history WHERE user_id=%s GROUP BY session_id ORDER BY last_at DESC LIMIT 20""",
        (customer_user_id,), fetch="all"
    )
    enriched = []
    import json as _j, re as _re
    for s in sessions:
        first_msg = execute_query(
            "SELECT user_message, detected_intent FROM chat_history WHERE user_id=%s AND session_id=%s ORDER BY created_at ASC LIMIT 1",
            (customer_user_id, s["session_id"]), fetch="one"
        )
        last_msg = execute_query(
            "SELECT ai_response FROM chat_history WHERE user_id=%s AND session_id=%s ORDER BY created_at DESC LIMIT 1",
            (customer_user_id, s["session_id"]), fetch="one"
        )
        title = (first_msg or {}).get("user_message", "Chat session")
        title = title[:60] + ("…" if len(title) > 60 else "")
        intent = (first_msg or {}).get("detected_intent") or "faq"
        p = ((last_msg or {}).get("ai_response", "")).strip()
        p = _re.sub(r'^```[\w]*\n?', '', p); p = _re.sub(r'```$', '', p).strip()
        if p.startswith('{'):
            try:
                obj = _j.loads(p)
                if isinstance(obj.get('assistant'), dict): p = obj['assistant'].get('message', p)
                else:
                    for k in ('message','response','reply','content','answer'):
                        if isinstance(obj.get(k), str): p = obj[k]; break
            except: pass
        enriched.append({**s, "title": title, "intent": intent, "preview": p[:100] + ("…" if len(p) > 100 else "")})
    return {"sessions": enriched, "customer_user_id": customer_user_id}


@router.delete("/history")
def clear_history(token_data: dict = Depends(verify_token)):
    """Clear all chat history for the current user."""
    user_id = int(token_data["sub"])
    execute_query("DELETE FROM chat_history WHERE user_id = %s", (user_id,), fetch="none")
    write_audit_log(user_id, "CHAT_HISTORY_CLEARED", "chat", None, "User cleared own chat history")
    return {"message": "Chat history cleared"}
