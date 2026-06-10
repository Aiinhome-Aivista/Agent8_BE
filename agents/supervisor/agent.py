import json
from typing import Dict, Any

class SupervisorAgent:
    """
    Coordinates the workflow and assigns tasks to sub-agents.
    """
    def __init__(self):
        self.name = "supervisor_agent"

    def process_request(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for handling chat requests.
        Routes to the Intent Agent first.
        """
        # In a real implementation, this would call the IntentAgent, then route to Policy/Escalation.
        # This is a stub for the agentic enhancement.
        from agents.intent.agent import IntentAgent
        
        intent_agent = IntentAgent()
        intent_result = intent_agent.analyze(message)
        
        return {
            "status": "success",
            "routed_to": intent_result.get("intent", "faq"),
            "response": f"[Agentic Backend] Processed via Supervisor. Intent detected: {intent_result.get('intent')}",
            "intent": intent_result.get("intent"),
            "confidence": intent_result.get("confidence")
        }
