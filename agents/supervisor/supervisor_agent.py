import uuid
from agents.base_agent import BaseAgent
from agents.intent.intent_agent import IntentAgent
from agents.policy.policy_agent import PolicyAgent
from agents.rag.rag_agent import RAGAgent
from agents.escalation.escalation_agent import EscalationAgent
from agents.renewal.renewal_agent import RenewalAgent
from agents.compliance.compliance_agent import ComplianceAgent
from agents.document.document_agent import DocumentAgent
from agents.guardrails.guardrail_agent import GuardrailAgent
from agents.auth.auth_agent import AuthAgent
from agents.approval.approval_agent import ApprovalAgent
from services.memory.memory_service import MemoryService

class SupervisorAgent(BaseAgent):
    def __init__(self):
        super().__init__("SupervisorAgent")
        self.intent_agent = IntentAgent()
        self.guardrail_agent = GuardrailAgent()
        self.memory_service = MemoryService()
        
        # Initialize Workers
        self.workers = {
            "PolicyAgent": PolicyAgent(),
            "RAGAgent": RAGAgent(),
            "EscalationAgent": EscalationAgent(),
            "RenewalAgent": RenewalAgent(),
            "ComplianceAgent": ComplianceAgent(),
            "DocumentAgent": DocumentAgent(),
            "AuthAgent": AuthAgent(),
            "ApprovalAgent": ApprovalAgent()
        }
        
        self.routing_matrix = {
            "policy_inquiry": "PolicyAgent",
            "policy_period": "PolicyAgent",
            "coverage_question": "RAGAgent",
            "faq": "RAGAgent",
            "renewal": "RenewalAgent",
            "address_update": "EscalationAgent",
            "phone_update": "EscalationAgent",
            "email_update": "EscalationAgent",
            "nominee_update": "EscalationAgent",
            "complaint": "EscalationAgent",
            "human_agent_request": "EscalationAgent",
            "policy_cancellation": "ComplianceAgent",
            "document_request": "DocumentAgent",
            "verify_otp": "AuthAgent",
            "coverage_increase": "ApprovalAgent",
            "nominee_removal": "ApprovalAgent",
            "high_risk_endorsement": "ApprovalAgent"
        }

    def execute(self, input_data):
        user_input = input_data.get("user_input")
        user_id = input_data.get("user_id")
        session_id = input_data.get("session_id", str(uuid.uuid4()))
        
        # 1. Input Guardrails
        guard_result = self.guardrail_agent.run({"text": user_input, "mode": "input"})
        if guard_result.get("status") == "BLOCKED":
            return {"response": "I cannot process that request.", "session_id": session_id}

        # 2. Intent Classification
        intent_data = self.intent_agent.run({"user_input": user_input})
        detected_intent = intent_data.get("intent", "unknown")
        
        # Save intent to memory
        self.memory_service.update_session_memory(session_id, user_id, {"history": [user_input], "last_intent": detected_intent})

        # 3. Route to Worker
        worker_name = self.routing_matrix.get(detected_intent)
        
        # Security Flow: Policy details require Auth
        if worker_name == "PolicyAgent":
            session_context = self.memory_service.get_session_memory(session_id)
            if session_context.get("auth_status") != "VERIFIED":
                worker_name = "AuthAgent"
                detected_intent = "generate_otp"
                input_data["action"] = "generate_otp"
        elif detected_intent == "verify_otp":
            input_data["action"] = "verify_otp"
            input_data["otp"] = user_input.strip()

        if worker_name and worker_name in self.workers:
            worker = self.workers[worker_name]
            
            # Map parameters based on worker
            worker_input = self._prepare_worker_input(detected_intent, input_data, session_id)
            
            worker_output = worker.run(worker_input, workflow_id=session_id)
            response = worker_output.get("response") or worker_output.get("message") or worker_output.get("ai_summary") or "Action processed."
        else:
            response = "I'm not sure how to handle that right now."

        # 4. Output Guardrails (PII Masking)
        masked_response = self.guardrail_agent.run({"text": response, "mode": "output"})
        
        return {
            "response": masked_response.get("masked_text", response),
            "session_id": session_id,
            "intent": detected_intent,
            "worker_used": worker_name
        }

    def _prepare_worker_input(self, intent, original_input, session_id):
        base_input = {
            "user_id": original_input.get("user_id"),
            "session_id": session_id
        }
        
        if intent in ["policy_inquiry"]:
            base_input["query_type"] = "policy_number"
        elif intent in ["policy_period"]:
            base_input["query_type"] = "policy_period"
        elif intent in ["coverage_question", "faq"]:
            base_input["query"] = original_input.get("user_input")
        elif intent in ["address_update", "phone_update", "email_update", "nominee_update", "complaint", "human_agent_request"]:
            base_input["issue_type"] = intent
        elif intent == "renewal":
            base_input["policy_id"] = original_input.get("policy_id")
        elif intent == "policy_cancellation":
            base_input["action"] = intent
            base_input["reference_id"] = original_input.get("policy_id")
            
        return base_input
