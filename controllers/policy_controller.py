# api/controllers/policy_controller.py
# GET /policies, GET /policies/{id}, GET /policies/{id}/coverage

import json
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException
from database.db import execute_query
from middleware.jwt_auth import verify_token, require_role
from utils.common import write_audit_log

router = APIRouter(prefix="/policies", tags=["Policies"])


@router.get("")
def list_policies(token_data: dict = Depends(verify_token)):
    """Return all policies for the logged-in customer (or all if CSR/supervisor)."""
    user_id = int(token_data["sub"])
    role = token_data["role"]

    if role == "customer":
        policies = execute_query(
            """SELECT p.*, 
                      DATEDIFF(p.expiry_date, CURDATE()) as days_to_expiry
               FROM policies p WHERE p.customer_id = %s ORDER BY p.created_at DESC""",
            (user_id,), fetch="all"
        )
    else:
        policies = execute_query(
            """SELECT p.*, u.name as customer_name, u.email as customer_email,
                      DATEDIFF(p.expiry_date, CURDATE()) as days_to_expiry
               FROM policies p JOIN users u ON p.customer_id = u.id 
               ORDER BY p.created_at DESC""",
            fetch="all"
        )

    # Parse JSON fields
    for p in policies:
        if p.get("policy_details") and isinstance(p["policy_details"], str):
            try:
                p["policy_details"] = json.loads(p["policy_details"])
            except Exception:
                p["policy_details"] = {}

    return {"policies": policies, "total": len(policies)}


@router.get("/{policy_id}")
def get_policy(policy_id: int, token_data: dict = Depends(verify_token)):
    """Return full details of a single policy."""
    user_id = int(token_data["sub"])
    role = token_data["role"]

    policy = execute_query(
        """SELECT p.*, u.name as customer_name, u.email as customer_email, u.phone as customer_phone,
                  DATEDIFF(p.expiry_date, CURDATE()) as days_to_expiry
           FROM policies p JOIN users u ON p.customer_id = u.id WHERE p.id = %s""",
        (policy_id,), fetch="one"
    )

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    # Customers can only view their own policies
    if role == "customer" and policy["customer_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if policy.get("policy_details") and isinstance(policy["policy_details"], str):
        try:
            policy["policy_details"] = json.loads(policy["policy_details"])
        except Exception:
            policy["policy_details"] = {}

    # Fetch renewal history
    renewals = execute_query(
        "SELECT * FROM renewals WHERE policy_id = %s ORDER BY renewed_at DESC",
        (policy_id,), fetch="all"
    )
    policy["renewal_history"] = renewals

    write_audit_log(user_id, "POLICY_VIEWED", "policy", policy_id, f"Viewed policy {policy['policy_number']}")
    return policy


@router.get("/{policy_id}/coverage")
def get_coverage(policy_id: int, token_data: dict = Depends(verify_token)):
    """Return coverage details for a policy."""
    user_id = int(token_data["sub"])
    policy = execute_query(
        "SELECT * FROM policies WHERE id = %s AND customer_id = %s",
        (policy_id, user_id), fetch="one"
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found or access denied")

    # Coverage details per policy type
    coverage_map = {
        "Motor Insurance": {
            "Own Damage": "Covered",
            "Third Party Liability": "Up to ₹15 Lakh",
            "Personal Accident": "₹15 Lakh",
            "Natural Calamities": "Covered",
            "Theft": "Covered",
            "Cashless Garages": "7,000+ across India",
            "Zero Depreciation": "Available as add-on",
            "Roadside Assistance": "24/7 Available",
        },
        "Health Insurance": {
            "Hospitalisation": "Covered (Room Rent: ₹5,000/day)",
            "Pre-Hospitalisation": "30 days",
            "Post-Hospitalisation": "60 days",
            "Day Care Procedures": "All 541 procedures covered",
            "Ambulance": "₹5,000 per hospitalisation",
            "Maternity": "Covered after 2 years waiting",
            "Critical Illness": "Available as add-on",
            "No-Claim Bonus": "10% cumulative bonus",
        },
        "Term Life": {
            "Death Benefit": f"₹{policy['coverage_amount']:,.0f}",
            "Accidental Death Benefit": "2x Sum Assured",
            "Terminal Illness": "50% advance payout",
            "Premium Waiver": "On critical illness",
            "Tax Benefit": "Section 80C + 10(10D)",
        },
        "Home Insurance": {
            "Building Structure": "Covered",
            "Contents & Belongings": "Covered",
            "Fire & Explosion": "Covered",
            "Theft & Burglary": "Covered",
            "Natural Calamities": "Covered (flood, earthquake)",
            "Tenant Liability": "Covered",
            "Rent Loss": "Up to 12 months",
        },
    }

    # Check for dynamically extracted coverage details
    dynamic_coverage = None
    if policy.get("policy_details") and isinstance(policy["policy_details"], str):
        try:
            details_json = json.loads(policy["policy_details"])
            if details_json.get("coverage_details"):
                dynamic_coverage = details_json["coverage_details"]
        except Exception:
            pass
            
    coverage = dynamic_coverage or coverage_map.get(policy["policy_type"], {"General Coverage": "As per policy terms"})
    return {
        "policy_number": policy["policy_number"],
        "policy_type": policy["policy_type"],
        "sum_insured": policy["coverage_amount"],
        "premium": policy["premium"],
        "coverage_details": coverage,
    }
