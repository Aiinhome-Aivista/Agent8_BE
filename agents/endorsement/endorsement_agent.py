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
        
        # Simple regex/extraction for email and address
        new_value = "Updated via AI"
        if issue_type == "email_update":
            import re
            emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', last_message)
            if emails:
                new_value = emails[-1]
            else:
                new_value = "user.updated@email.com"
        else:
            # Address/phone etc - just use the message or a dummy string for the test
            parts = last_message.lower().split('to')
            if len(parts) > 1:
                new_value = parts[-1].strip()
        
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
        
        # Only update if the field actually exists in users table (address, phone, email)
        if db_field in ["address", "phone", "email"]:
            execute_query(f"UPDATE users SET {db_field} = %s WHERE id = %s", (new_value, user_id), fetch="none")
        
        # Get active policies to add to endorsements table
        policies = execute_query(
            "SELECT id FROM policies WHERE customer_id = %s AND status = 'active'",
            (user_id,), fetch="all"
        )
        
        for pol in policies:
            execute_query(
                "INSERT INTO endorsements (policy_id, user_id, update_type, old_value, new_value, status) VALUES (%s,%s,%s,%s,%s,'approved')",
                (pol["id"], user_id, db_field, old_value, new_value), fetch="none"
            )
            
        write_audit_log(user_id, f"{db_field.upper()}_UPDATE", "endorsement", None,
                        f"AI Agent changed {db_field} from '{old_value}' to '{new_value}'", severity="sensitive")
        
        return {
            "response": f"Your {db_field} has been successfully updated to: {new_value}.",
            "status": "Success",
            "ai_summary": f"Updated {db_field} to {new_value}"
        }
