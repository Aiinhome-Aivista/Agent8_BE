from agents.base_agent import BaseAgent

class ApprovalAgent(BaseAgent):
    def __init__(self):
        super().__init__("ApprovalAgent")

    def execute(self, input_data):
        action = input_data.get("action", "unknown_action")
        
        # Human in the Loop (HITL) Logic
        hitl_message = (
            f"⚠️ **Human Review Required**\n"
            f"Your request for '{action.replace('_', ' ').title()}' falls under sensitive compliance workflows.\n"
            f"This action requires manual approval (Human-in-the-Loop) before execution.\n"
            f"It has been routed to the Enterprise Approval Queue. Our team will contact you shortly."
        )
        
        return {
            "response": hitl_message,
            "status": "PENDING_APPROVAL",
            "hitl_triggered": True
        }
