from agents.base_agent import BaseAgent
from services.sla.sla_service import SLAService

class SLAAgent(BaseAgent):
    def __init__(self):
        super().__init__("SLAAgent")
        self.sla_service = SLAService()

    def execute(self, input_data):
        action = input_data.get("action")
        
        if action == "check_breaches":
            # This is typically called by a background job
            self.sla_service.check_breaches()
            return {"status": "Breaches checked and escalated"}
            
        elif action == "track_entity":
            entity_type = input_data.get("entity_type")
            entity_id = input_data.get("entity_id")
            rule_name = input_data.get("rule_name")
            
            self.sla_service.track_entity(entity_type, entity_id, rule_name)
            return {"status": "SLA Tracking Started"}

        return {"status": "Invalid action"}
