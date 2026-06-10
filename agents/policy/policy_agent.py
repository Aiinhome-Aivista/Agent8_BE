from agents.base_agent import BaseAgent
from database.db import fetch_one

class PolicyAgent(BaseAgent):
    def __init__(self):
        super().__init__("PolicyAgent")

    def execute(self, input_data):
        user_id = input_data.get("user_id")
        query_type = input_data.get("query_type") # e.g., 'policy_number', 'policy_period', 'coverage'
        
        # In a real scenario, this fetches from the policies table
        # Since I'm not to delete/modify existing tables, I'll assume standard columns
        
        if query_type == "policy_number":
            policy = fetch_one("SELECT policy_number FROM policies WHERE user_id = %s", (user_id,))
            return {"response": f"Your policy number is {policy['policy_number']}" if policy else "No policy found."}
        
        elif query_type == "policy_period":
            policy = fetch_one("SELECT start_date, end_date FROM policies WHERE user_id = %s", (user_id,))
            if policy:
                return {"response": f"Your policy period is from {policy['start_date']} to {policy['end_date']}"}
            return {"response": "No policy period information found."}
            
        elif query_type == "coverage":
            policy = fetch_one("SELECT coverage_details FROM policies WHERE user_id = %s", (user_id,))
            if policy:
                return {"response": f"Your coverage includes: {policy['coverage_details']}"}
            return {"response": "No coverage information found."}
            
        else:
            return {"response": "I can help you with your policy number, period, or coverage."}
