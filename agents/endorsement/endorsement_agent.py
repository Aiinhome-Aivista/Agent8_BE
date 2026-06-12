import requests
from agents.base_agent import BaseAgent
from database.db import execute_query
from services.memory.memory_service import MemoryService
from utils.common import write_audit_log

class EndorsementAgent(BaseAgent):
    def __init__(self):
        super().__init__("EndorsementAgent")
        self.memory_service = MemoryService()

    def execute(self, input_data):
        user_id = input_data.get("user_id")
        issue_type = input_data.get("issue_type") # e.g., 'address_update', 'email_update'
        session_id = input_data.get("session_id")
        
        session_context = self.memory_service.get_session_memory(session_id)
        chat_history = session_context.get("history", [])
        
        # We need to know what the new value is. For simplicity in the AI demo, 
        # we will extract it from the last user message, or assume a dummy value 
        # since the prompt didn't specify exactly how to extract the new email/address robustly.
        # Flow 3 prompt: "I want to update my email address to new.email@test.com"
        
        last_message = chat_history[-1] if chat_history else ""
        
        # Extract new value more robustly
        new_value = None
        last_lower = last_message.lower()
        
        if issue_type == "email_update":
            import re
            emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', last_message)
            if emails:
                new_value = emails[-1]
        else:
            if ' to ' in last_lower:
                val = last_message[last_lower.rfind(' to ')+4:].strip()
                if len(val) > 2 and "update" not in val.lower() and "change" not in val.lower():
                    new_value = val
                    
        if not new_value:
            return {
                "response": "Please provide the new value in your request. For example: 'Update my address to 123 Main St'.",
                "status": "Failed",
                "ai_summary": "Failed to extract new value from user input."
            }
        
        update_field_map = {
            "address_update": "address",
            "phone_update": "phone",
            "email_update": "email",
            "nominee_update": "nominee"
        }
        
        db_field = update_field_map.get(issue_type, "address")
        
        # Apply the endorsement (similar to endorsement_controller)
        user = execute_query(f"SELECT {db_field} FROM users WHERE id = %s", (user_id,), fetch="one")
        old_value = user.get(db_field, "") if user else ""
        
        # We NO LONGER update the users table directly via AI to require CSR review.
        # if db_field in ["address", "phone", "email"]:
        #     execute_query(f"UPDATE users SET {db_field} = %s WHERE id = %s", (new_value, user_id), fetch="none")
        
        # Get active policies to add to endorsements table
        policies = execute_query(
            "SELECT id FROM policies WHERE customer_id = %s AND status = 'active'",
            (user_id,), fetch="all"
        )
        
        for pol in policies:
            execute_query(
                "INSERT INTO endorsements (policy_id, user_id, update_type, old_value, new_value, status) VALUES (%s,%s,%s,%s,%s,'pending')",
                (pol["id"], user_id, db_field, old_value, new_value), fetch="none"
            )
            
        # Create an Escalation Ticket for CSR Review
        import uuid
        ticket_string = f"TCK-{uuid.uuid4().hex[:8].upper()}"
        ai_summary = f"User requested to update their {db_field} from '{old_value}' to '{new_value}'."
        query = """
            INSERT INTO escalations (ticket_id, user_id, issue, category, priority, status)
            VALUES (%s, %s, %s, %s, 'medium', 'OPEN')
        """
        # fetch="none" returns the lastrowid
        ticket_id = execute_query(query, (ticket_string, user_id, ai_summary, issue_type), fetch="none")
        
        # Track SLA for ticket
        if ticket_id:
            try:
                from services.sla.sla_service import SLAService
                SLAService().track_entity(entity_type='ticket', entity_id=ticket_id, rule_name='CSR Standard SLA')
            except ImportError:
                pass
            
        write_audit_log(user_id, f"{db_field.upper()}_UPDATE_REQUESTED", "endorsement", ticket_id,
                        f"AI Agent created ticket to change {db_field} from '{old_value}' to '{new_value}'", severity="sensitive")
        
        return {
            "response": f"I have raised a ticket ({ticket_string}) to update your {db_field} to: {new_value}. A human agent will review and process this shortly.",
            "status": "Escalated",
            "ai_summary": f"Requested update for {db_field} to {new_value}. Ticket created."
        }
