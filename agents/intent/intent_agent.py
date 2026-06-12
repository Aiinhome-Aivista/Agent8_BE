from agents.base_agent import BaseAgent
# pyrefly: ignore [missing-import]
from database.db import fetch_one

class IntentAgent(BaseAgent):
    def __init__(self):
        super().__init__("IntentAgent")
        
        # Load prompt template (fail-safe)
        try:
            template_record = fetch_one("SELECT template_text FROM prompt_templates WHERE agent_name = 'intent_classifier'")
            self.prompt_template = template_record['template_text'] if template_record else ""
        except Exception:
            self.prompt_template = ""

    def execute(self, input_data):
        user_input = input_data.get("user_input", "")
        
        # Simulated LLM Intent Classification (In production, call an LLM with self.prompt_template)
        detected_intent = "faq"
        confidence = 0.60
        
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
        elif "cover" in lower_input or "surgery" in lower_input or "feature" in lower_input or "benefit" in lower_input or "include" in lower_input:
            detected_intent = "coverage_question"
            confidence = 0.88
        elif "email" in lower_input and ("update" in lower_input or "change" in lower_input):
            detected_intent = "email_update"
            confidence = 0.93
        elif "phone" in lower_input and ("update" in lower_input or "change" in lower_input):
            detected_intent = "phone_update"
            confidence = 0.93
        elif "address" in lower_input and ("update" in lower_input or "change" in lower_input):
            detected_intent = "address_update"
            confidence = 0.92
        elif "renew" in lower_input:
            detected_intent = "renewal"
            confidence = 0.94
        elif "cancel" in lower_input or "frustrated" in lower_input or "terrible" in lower_input:
            detected_intent = "policy_cancellation"
            confidence = 0.96
        elif any(w in lower_input for w in ["complaint", "angry", "wrong", "problem"]):
            detected_intent = "complaint"
            confidence = 0.90
        elif any(w in lower_input for w in ["escalate", "human", "agent", "manager", "speak"]):
            detected_intent = "human_agent_request"
            confidence = 0.92
        elif any(w in lower_input for w in ["my", "i ", "uploaded", "approved", "claim"]):
            detected_intent = "personal_faq"
            confidence = 0.80
        elif any(w in lower_input for w in ["what", "how", "tell", "explain", "key", "about"]):
            detected_intent = "faq"
            confidence = 0.75
        elif "document" in lower_input or "download" in lower_input:
            detected_intent = "document_request"
            confidence = 0.85

        return {
            "intent": detected_intent,
            "confidence": confidence
        }

