from typing import Dict, Any

class IntentAgent:
    """
    Analyzes incoming user requests to determine the required workflow.
    """
    def __init__(self):
        self.name = "intent_agent"

    def analyze(self, message: str) -> Dict[str, Any]:
        """
        Classifies the intent of the message.
        """
        # Stub logic
        message_lower = message.lower()
        if "update" in message_lower or "address" in message_lower:
            return {"intent": "address_update", "confidence": 0.95}
        elif "policy" in message_lower:
            return {"intent": "policy_inquiry", "confidence": 0.85}
        
        return {"intent": "faq", "confidence": 0.70}
