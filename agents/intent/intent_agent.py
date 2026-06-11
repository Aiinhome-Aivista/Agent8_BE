from agents.base_agent import BaseAgent
# pyrefly: ignore [missing-import]
from database.db import fetch_one

class IntentAgent(BaseAgent):
    def __init__(self):
        super().__init__("IntentAgent")
        
        # Load prompt template
        template_record = fetch_one("SELECT template_content FROM prompt_templates WHERE agent_name = 'intent_classifier'")
        self.prompt_template = template_record['template_content'] if template_record else ""

    def execute(self, input_data):
        user_input = input_data.get("user_input", "")
        
        # Simulated LLM Intent Classification (In production, call an LLM with self.prompt_template)
        detected_intent = "unknown"
        confidence = 0.0
        
        import re
        lower_input = user_input.lower()
        
        # Check for 6-digit OTP first
        if re.fullmatch(r"\b\d{6}\b", user_input.strip()):
            return {"intent": "verify_otp", "confidence": 0.99}
            
        if "policy number" in lower_input:
            detected_intent = "policy_inquiry"
            confidence = 0.95
        elif "period" in lower_input:
            detected_intent = "policy_period"
            confidence = 0.90
        elif "remove nominee" in lower_input or "delete nominee" in lower_input:
            detected_intent = "nominee_removal"
            confidence = 0.95
        elif "increase cover" in lower_input:
            detected_intent = "coverage_increase"
            confidence = 0.92
        elif "cover" in lower_input or "surgery" in lower_input:
            detected_intent = "coverage_question"
            confidence = 0.88
        elif "address" in lower_input:
            detected_intent = "address_update"
            confidence = 0.92
        elif "renew" in lower_input:
            detected_intent = "renewal"
            confidence = 0.94
        elif "cancel" in lower_input:
            detected_intent = "policy_cancellation"
            confidence = 0.96

        return {
            "intent": detected_intent,
            "confidence": confidence
        }
