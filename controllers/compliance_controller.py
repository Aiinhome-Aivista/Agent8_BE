# api/controllers/compliance_controller.py
from fastapi import APIRouter, Depends, Query
from typing import Optional
from database.db import execute_query
from middleware.jwt_auth import require_role
from utils.common import write_audit_log
import csv, io
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/compliance", tags=["Compliance"])

def _compliance_dep():
    return require_role("compliance", "supervisor")

@router.get("/audit-logs")
def get_audit_logs(
    page: int = 1,
    page_size: int = 50,
    action: Optional[str] = None,
    severity: Optional[str] = None,
    user_id_filter: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    token_data: dict = Depends(require_role("compliance", "supervisor"))
):
    where, params = [], []
    if action:
        where.append("a.action = %s"); params.append(action)
    if severity:
        where.append("a.severity = %s"); params.append(severity)
    if user_id_filter:
        where.append("a.user_id = %s"); params.append(user_id_filter)
    if date_from:
        where.append("DATE(a.created_at) >= %s"); params.append(date_from)
    if date_to:
        where.append("DATE(a.created_at) <= %s"); params.append(date_to)

    w = "WHERE " + " AND ".join(where) if where else ""
    offset = (page - 1) * page_size

    rows = execute_query(
        f"""SELECT a.*, u.name as user_name, u.role as user_role FROM audit_logs a
            LEFT JOIN users u ON a.user_id = u.id {w}
            ORDER BY a.created_at DESC LIMIT %s OFFSET %s""",
        tuple(params) + (page_size, offset), fetch="all"
    )
    total = execute_query(f"SELECT COUNT(*) as cnt FROM audit_logs a {w}", tuple(params), fetch="one")

    return {"logs": rows, "total": total["cnt"], "page": page, "page_size": page_size}

@router.get("/guardrail-violations")
def get_guardrail_violations(
    page: int = 1,
    token_data: dict = Depends(require_role("compliance", "supervisor"))
):
    offset = (page - 1) * 20
    rows = execute_query(
        """SELECT g.*, u.name as user_name, u.email as user_email FROM guardrail_logs g
           LEFT JOIN users u ON g.user_id = u.id ORDER BY g.created_at DESC LIMIT 20 OFFSET %s""",
        (offset,), fetch="all"
    )
    total = execute_query("SELECT COUNT(*) as cnt FROM guardrail_logs", fetch="one")
    return {"violations": rows, "total": total["cnt"]}

@router.get("/sensitive-actions")
def get_sensitive_actions(token_data: dict = Depends(require_role("compliance", "supervisor"))):
    rows = execute_query(
        """SELECT a.*, u.name as user_name FROM audit_logs a LEFT JOIN users u ON a.user_id=u.id
           WHERE a.severity IN ('sensitive','high') ORDER BY a.created_at DESC LIMIT 100""",
        fetch="all"
    )
    return {"actions": rows, "total": len(rows)}

@router.get("/summary")
def get_compliance_summary(token_data: dict = Depends(require_role("compliance", "supervisor"))):
    total_logs = execute_query("SELECT COUNT(*) as cnt FROM audit_logs", fetch="one")
    guardrail_count = execute_query("SELECT COUNT(*) as cnt FROM guardrail_logs WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)", fetch="one")
    sensitive_count = execute_query("SELECT COUNT(*) as cnt FROM audit_logs WHERE severity='sensitive' AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)", fetch="one")
    high_count = execute_query("SELECT COUNT(*) as cnt FROM audit_logs WHERE severity='high' AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)", fetch="one")
    action_breakdown = execute_query(
        "SELECT action, COUNT(*) as cnt FROM audit_logs GROUP BY action ORDER BY cnt DESC LIMIT 10", fetch="all"
    )
    return {
        "total_audit_logs": total_logs["cnt"],
        "guardrail_violations_30d": guardrail_count["cnt"],
        "sensitive_actions_30d": sensitive_count["cnt"],
        "high_severity_30d": high_count["cnt"],
        "action_breakdown": action_breakdown,
        "compliance_score": 96,
    }

@router.get("/export")
def export_audit_logs(
    format: str = "csv",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    token_data: dict = Depends(require_role("compliance", "supervisor"))
):
    where, params = [], []
    if date_from:
        where.append("DATE(a.created_at) >= %s"); params.append(date_from)
    if date_to:
        where.append("DATE(a.created_at) <= %s"); params.append(date_to)
    w = "WHERE " + " AND ".join(where) if where else ""

    rows = execute_query(
        f"""SELECT a.id, u.name as user_name, u.email, a.action, a.entity_type, a.details, a.severity, a.created_at
            FROM audit_logs a LEFT JOIN users u ON a.user_id=u.id {w} ORDER BY a.created_at DESC LIMIT 10000""",
        tuple(params), fetch="all"
    )

    user_id = int(token_data["sub"])
    write_audit_log(user_id, "BULK_EXPORT", "compliance", None, f"Exported {len(rows)} audit records as {format}", severity="sensitive")

    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        for row in rows:
            writer.writerow({k: str(v) if v is not None else "" for k, v in row.items()})

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=insureai_audit_export.csv"}
    )
