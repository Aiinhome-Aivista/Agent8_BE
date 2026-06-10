from agents.base_agent import BaseAgent
from services.approval.approval_service import ApprovalService

class ComplianceAgent(BaseAgent):
    def __init__(self):
        super().__init__("ComplianceAgent")
        self.approval_service = ApprovalService()

    def execute(self, input_data):
        user_id = input_data.get("user_id")
        action = input_data.get("action") # e.g., 'policy_cancellation'
        reference_id = input_data.get("reference_id")
        
        if action == "policy_cancellation":
            # Requires compliance approval
            req_id = self.approval_service.create_approval_request(
                request_type="POLICY_CANCELLATION",
                reference_id=reference_id,
                requested_by=user_id
            )
            return {
                "status": "Pending Compliance Review",
                "approval_request_id": req_id,
                "message": "Your request to cancel the policy has been sent to the Compliance team for manual review."
            }
            
        return {"status": "Unknown action"}
