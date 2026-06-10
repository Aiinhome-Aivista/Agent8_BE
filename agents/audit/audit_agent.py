from agents.base_agent import BaseAgent
from services.audit.audit_service import AuditService

class AuditAgent(BaseAgent):
    def __init__(self):
        super().__init__("AuditAgent")
        self.audit_service = AuditService()

    def execute(self, input_data):
        user_id = input_data.get("user_id")
        event_type = input_data.get("event_type")
        details = input_data.get("details")
        
        self.audit_service.log_audit_event(
            user_id=user_id,
            event_type=event_type,
            details=details
        )
        
        return {"status": "Audit Logged"}
