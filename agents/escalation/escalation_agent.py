from agents.base_agent import BaseAgent
from database.db import execute_query
from services.sla.sla_service import SLAService
from services.memory.memory_service import MemoryService

class EscalationAgent(BaseAgent):
    def __init__(self):
        super().__init__("EscalationAgent")
        self.sla_service = SLAService()
        self.memory_service = MemoryService()

    def execute(self, input_data):
        user_id = input_data.get("user_id")
        issue_type = input_data.get("issue_type") # e.g., 'address_update', 'complaint'
        session_id = input_data.get("session_id")
        
        # Get chat history for AI summary
        session_context = self.memory_service.get_session_memory(session_id)
        chat_history = session_context.get("history", [])
        
        # Simulated AI Summary generation
        ai_summary = f"User wants to {issue_type}. Escalation recommended."
        
        import uuid
        ticket_id_str = f"TKT-{str(uuid.uuid4())[:8].upper()}"
        
        from utils.common import get_least_busy_csr
        assigned_to = get_least_busy_csr()
        
        # Create Ticket
        query = """
            INSERT INTO escalations (ticket_id, user_id, category, issue, status, assigned_to)
            VALUES (%s, %s, %s, %s, 'OPEN', %s)
        """
        db_id = execute_query(query, (ticket_id_str, user_id, issue_type, ai_summary, assigned_to), fetch="none")
        
        if db_id:
            # Track SLA
            self.sla_service.track_entity(entity_type='ticket', entity_id=db_id, rule_name='CSR Standard SLA')
            
            return {
                "status": "Escalated",
                "ticket_id": ticket_id_str,
                "ai_summary": ai_summary,
                "assigned_to": "CSR Pool"
            }
        return {"status": "Failed to escalate"}
