# api/controllers/dashboard_controller.py
from fastapi import APIRouter, Depends
from database.db import execute_query
from middleware.jwt_auth import verify_token

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/customer")
def customer_dashboard(token_data: dict = Depends(verify_token)):
    user_id = int(token_data["sub"])
    role = token_data.get("role", "customer")
    policies = execute_query(
        "SELECT COUNT(*) as total, SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) as active, SUM(CASE WHEN status='expired' THEN 1 ELSE 0 END) as expired, SUM(premium) as total_premium, SUM(coverage_amount) as total_coverage FROM policies WHERE customer_id=%s",
        (user_id,), fetch="one"
    )
    expiring_soon = execute_query(
        "SELECT policy_number, policy_type, expiry_date, DATEDIFF(expiry_date, CURDATE()) as days FROM policies WHERE customer_id=%s AND status='active' AND DATEDIFF(expiry_date, CURDATE()) BETWEEN 0 AND 90 ORDER BY expiry_date",
        (user_id,), fetch="all"
    )
    open_tickets = execute_query(
        "SELECT COUNT(*) as cnt FROM escalations WHERE user_id=%s AND status IN ('open','in-progress')", (user_id,), fetch="one"
    )
    recent_activity = execute_query(
        "SELECT action, details, created_at FROM audit_logs WHERE user_id=%s ORDER BY created_at DESC LIMIT 5", (user_id,), fetch="all"
    )
    unread_notifs = execute_query(
        "SELECT COUNT(*) as cnt FROM notifications WHERE user_id=%s AND status='unread'", (user_id,), fetch="one"
    )

    # ── KB Vector Search: find relevant company KB docs for this customer ──────
    kb_insights = []
    try:
        from utils.kb_helper import search_kb_documents
        active_pol_rows = execute_query(
            "SELECT policy_type, coverage_amount FROM policies WHERE customer_id=%s AND status='active'",
            (user_id,), fetch="all"
        )
        kb_query = "insurance policy coverage benefits"
        if active_pol_rows:
            kb_query += " " + " ".join(p["policy_type"] for p in active_pol_rows)
        chunks = search_kb_documents(kb_query, top_k=3, user_id=user_id, user_role=role)
        kb_insights = [c[:300].strip() + ("…" if len(c) > 300 else "") for c in chunks if c.strip()]
    except Exception as e:
        print(f"[WARN] KB vector search on dashboard failed: {e}")

    # ── Doc-based policy extraction (fallback when SQL policies table is empty) ─
    doc_policies = None
    if not policies or (policies.get("active") or 0) == 0:
        try:
            from utils.local_llm_helper import _chat
            import json as _json

            # Get the customer's name to use as a KB search filter
            user_row = execute_query("SELECT name FROM users WHERE id=%s", (user_id,), fetch="one")
            customer_name = (user_row or {}).get("name", "")

            context_chunks = []

            # ── Level 1: personal uploaded_documents ──────────────────────────
            doc_count = execute_query(
                "SELECT COUNT(*) as cnt FROM uploaded_documents WHERE user_id=%s AND is_processed=1",
                (user_id,), fetch="one"
            )
            if doc_count and doc_count["cnt"] > 0:
                from utils.rag_helper import search_documents
                context_chunks = search_documents(
                    user_id, "policy premium coverage sum insured policy number", top_k=5
                )
                print(f"[INFO] Dashboard: {len(context_chunks)} chunks from personal docs for user {user_id}")

            # ── Level 2: company KB — search by customer name ─────────────────
            if not context_chunks and customer_name:
                from utils.kb_helper import search_kb_documents
                name_chunks = search_kb_documents(
                    f"{customer_name} policy premium coverage sum insured", top_k=6, user_id=user_id, user_role=role
                )
                # Keep only chunks that actually contain the customer's name
                # (to avoid picking up generic company docs)
                name_lower = customer_name.lower()
                context_chunks = [c for c in name_chunks if name_lower in c.lower()]
                if not context_chunks:
                    # Broader fallback: any KB chunk with policy/premium data
                    context_chunks = name_chunks
                print(f"[INFO] Dashboard: {len(context_chunks)} chunks from company KB for '{customer_name}'")

            if context_chunks:
                context = "\n\n---\n\n".join(context_chunks[:5])
                prompt = (
                    "From the following insurance policy document excerpts, extract ONLY these fields as JSON.\n"
                    "Return ONLY valid JSON, no explanation.\n"
                    "Fields:\n"
                    "  active_count   : int   — number of active policies (default 1 if not stated)\n"
                    "  total_coverage : float — sum insured / coverage amount in INR (numbers only, no commas)\n"
                    "  annual_premium : float — annual premium in INR (numbers only, no commas)\n"
                    "  policy_number  : string — full policy number\n"
                    "  insurer        : string — insurance company name\n"
                    "  policy_type    : string — type of policy (Health, Motor, Life, etc.)\n"
                    "Use null for any field not found.\n\n"
                    f"DOCUMENTS:\n{context}"
                )
                resp = _chat(
                    model="mistral:latest",
                    messages=[
                        {"role": "system", "content": "You extract structured data from insurance documents. Return ONLY valid JSON, no markdown fences."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500, temperature=0, json_mode=True
                )
                raw = resp["choices"][0]["message"]["content"].strip()
                import re
                # Try to extract just the JSON array or object
                match = re.search(r'(\[.*\]|\{.*\})', raw, re.DOTALL)
                if match:
                    raw = match.group(1)
                else:
                    raw = raw.replace("```json", "").replace("```", "").strip()
                
                try:
                    extracted = _json.loads(raw)
                except _json.JSONDecodeError:
                    print(f"[WARN] Failed to parse JSON, returning empty. Raw: {raw}")
                    extracted = {}
                
                if isinstance(extracted, list):
                    extracted = extracted[0] if len(extracted) > 0 else {}
                doc_policies = {
                    "active":         int(extracted.get("active_count") or 1),
                    "total":          int(extracted.get("active_count") or 1),
                    "expired":        0,
                    "total_premium":  float(str(extracted.get("annual_premium") or 0).replace(",", "")),
                    "total_coverage": float(str(extracted.get("total_coverage") or 0).replace(",", "")),
                    "policy_number":  extracted.get("policy_number"),
                    "insurer":        extracted.get("insurer"),
                    "policy_type":    extracted.get("policy_type"),
                    "source":         "kb_documents" if not (doc_count and doc_count.get("cnt", 0) > 0) else "uploaded_documents",
                }
                print(f"[INFO] doc_policies for user {user_id}: {doc_policies}")
        except Exception as e:
            print(f"[WARN] Doc-based policy extraction failed: {e}")

    return {
        "policies": policies,
        "doc_policies": doc_policies,       # non-null when extracted from uploaded/KB docs
        "expiring_soon": expiring_soon,
        "open_tickets": open_tickets["cnt"],
        "recent_activity": recent_activity,
        "unread_notifications": unread_notifs["cnt"],
        "kb_insights": kb_insights,
    }


@router.get("/supervisor")
def supervisor_dashboard(token_data: dict = Depends(verify_token)):
    role = token_data["role"]
    if role not in ("supervisor", "compliance"):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Access denied")

    total_chats = execute_query("SELECT COUNT(*) as cnt FROM chat_history WHERE DATE(created_at) = CURDATE()", fetch="one")
    total_chats_week = execute_query("SELECT COUNT(*) as cnt FROM chat_history WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)", fetch="one")
    open_esc = execute_query("SELECT COUNT(*) as cnt FROM escalations WHERE status IN ('open','in-progress')", fetch="one")
    resolved_today = execute_query("SELECT COUNT(*) as cnt FROM escalations WHERE status='resolved' AND DATE(updated_at)=CURDATE()", fetch="one")
    total_users = execute_query("SELECT COUNT(*) as cnt FROM users WHERE role='customer'", fetch="one")
    total_policies = execute_query("SELECT COUNT(*) as cnt, SUM(premium) as total_premium FROM policies WHERE status='active'", fetch="one")
    renewals_today = execute_query("SELECT COUNT(*) as cnt, COALESCE(SUM(amount),0) as amount FROM renewals WHERE DATE(renewed_at)=CURDATE()", fetch="one")

    # Intent distribution (last 7 days)
    intent_dist = execute_query(
        "SELECT detected_intent, COUNT(*) as cnt FROM chat_history WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) AND detected_intent IS NOT NULL GROUP BY detected_intent ORDER BY cnt DESC",
        fetch="all"
    )
    # Daily chat volume (last 7 days)
    daily_volume = execute_query(
        "SELECT DATE(created_at) as date, COUNT(*) as cnt FROM chat_history WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) GROUP BY DATE(created_at) ORDER BY date",
        fetch="all"
    )
    escalation_by_priority = execute_query(
        "SELECT priority, COUNT(*) as cnt FROM escalations WHERE status IN ('open','in-progress') GROUP BY priority",
        fetch="all"
    )
    top_csrs = execute_query(
        "SELECT u.name, COUNT(*) as ticket_count, SUM(CASE WHEN e.status='resolved' THEN 1 ELSE 0 END) as resolved FROM escalations e JOIN users u ON e.assigned_to=u.id WHERE u.role='csr' GROUP BY e.assigned_to, u.name ORDER BY resolved DESC LIMIT 5",
        fetch="all"
    )
    return {
        "today_chats": total_chats["cnt"],
        "week_chats": total_chats_week["cnt"],
        "open_escalations": open_esc["cnt"],
        "resolved_today": resolved_today["cnt"],
        "total_customers": total_users["cnt"],
        "active_policies": total_policies["cnt"],
        "total_premium_active": float(total_policies["total_premium"] or 0),
        "renewals_today": renewals_today["cnt"],
        "renewal_revenue_today": float(renewals_today["amount"] or 0),
        "intent_distribution": intent_dist,
        "daily_volume": daily_volume,
        "escalation_by_priority": escalation_by_priority,
        "top_csrs": top_csrs,
    }

@router.get("/csr")
def csr_dashboard(token_data: dict = Depends(verify_token)):
    if token_data["role"] != "csr":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="CSR only")
    user_id = int(token_data["sub"])
    assigned = execute_query("SELECT COUNT(*) as cnt FROM escalations WHERE assigned_to=%s", (user_id,), fetch="one")
    open_mine = execute_query("SELECT COUNT(*) as cnt FROM escalations WHERE assigned_to=%s AND status='open'", (user_id,), fetch="one")
    in_prog = execute_query("SELECT COUNT(*) as cnt FROM escalations WHERE assigned_to=%s AND status='in-progress'", (user_id,), fetch="one")
    resolved_today = execute_query("SELECT COUNT(*) as cnt FROM escalations WHERE assigned_to=%s AND status='resolved' AND DATE(updated_at)=CURDATE()", (user_id,), fetch="one")
    recent = execute_query(
        """SELECT e.*, u.name as customer_name FROM escalations e JOIN users u ON e.user_id=u.id
           WHERE e.assigned_to=%s AND e.status IN ('open','in-progress')
           ORDER BY FIELD(e.priority,'critical','high','medium','low'), e.created_at DESC LIMIT 10""",
        (user_id,), fetch="all"
    )
    return {
        "assigned_total": assigned["cnt"],
        "open": open_mine["cnt"],
        "in_progress": in_prog["cnt"],
        "resolved_today": resolved_today["cnt"],
        "recent_tickets": recent,
    }
