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
from agents.endorsement.endorsement_agent import EndorsementAgent
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
            "ApprovalAgent": ApprovalAgent(),
            "EndorsementAgent": EndorsementAgent()
        }
        
        self.routing_matrix = {
            "policy_inquiry": "PolicyAgent",
            "policy_period": "PolicyAgent",
            "coverage_question": "RAGAgent",
            "faq": "RAGAgent",
            "personal_faq": "RAGAgent",
            "renewal": "RenewalAgent",
            "address_update": "EndorsementAgent",
            "phone_update": "EndorsementAgent",
            "email_update": "EndorsementAgent",
            "nominee_update": "EndorsementAgent",
            "complaint": "EscalationAgent",
            "human_agent_request": "EscalationAgent",
            "policy_cancellation": "EscalationAgent",
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
        
        # Save intent and history to memory
        mem = self.memory_service.get_session_memory(session_id)
        current_history = mem.get("history", [])
        current_history.append(user_input)
        turn_count = mem.get("turn_count", 0) + 1
        
        self.memory_service.update_session_memory(session_id, user_id, {
            "history": current_history, 
            "last_intent": detected_intent,
            "turn_count": turn_count
        })

        # 3. Route to Worker
        # OTP Check for personal queries
        if detected_intent == "personal_faq":
            mem = self.memory_service.get_session_memory(session_id)
            if not mem.get("otp_verified"):
                self.memory_service.update_session_memory(session_id, user_id, {
                    "state": "awaiting_otp", 
                    "pending_intent": "personal_faq", 
                    "pending_input": user_input
                })
                auth_input = {"action": "generate_otp", "user_id": user_id, "session_id": session_id}
                auth_result = self.workers["AuthAgent"].run(auth_input, workflow_id=session_id)
                return {
                    "response": f"For security reasons, I need to verify your identity before accessing your personal documents. {auth_result.get('message', 'An OTP has been sent.')}",
                    "session_id": session_id,
                    "intent": "verify_otp",
                    "worker_used": "AuthAgent"
                }

        worker_name = self.routing_matrix.get(detected_intent)
        was_otp_verified = False

        if worker_name and worker_name in self.workers:
            worker = self.workers[worker_name]
            
            # Map parameters based on worker
            worker_input = self._prepare_worker_input(detected_intent, input_data, session_id)
            
            worker_output = worker.run(worker_input)
            
            if detected_intent == "verify_otp" and worker_output.get("status") == "VERIFIED":
                was_otp_verified = True
                mem = self.memory_service.get_session_memory(session_id)
                self.memory_service.update_session_memory(session_id, user_id, {"otp_verified": True, "state": "active"})
                pending_intent = mem.get("pending_intent")
                pending_input_text = mem.get("pending_input")
                
                if pending_intent and pending_intent in self.routing_matrix:
                    pending_input_data = {
                        "user_input": pending_input_text,
                        "user_id": user_id,
                        "session_id": session_id
                    }
                    pending_worker_name = self.routing_matrix[pending_intent]
                    pending_worker = self.workers[pending_worker_name]
                    pending_worker_input = self._prepare_worker_input(pending_intent, pending_input_data, session_id)
                    pending_output = pending_worker.run(pending_worker_input, workflow_id=session_id)
                    
                    response = pending_output.get("response") or pending_output.get("message") or pending_output.get("ai_summary") or "Action processed."
                    detected_intent = pending_intent
                    worker_name = pending_worker_name
                else:
                    response = "OTP verified successfully. You can now proceed."
            else:
                response = worker_output.get("response") or worker_output.get("message") or worker_output.get("ai_summary") or "Action processed."
        else:
            response = "I'm not sure how to handle that right now."

        # 4. Output Guardrails (PII Masking)
        masked_response = self.guardrail_agent.run({"text": response, "mode": "output"})
        
        result_dict = {
            "response": masked_response.get("masked_text", response),
            "session_id": session_id,
            "intent": detected_intent,
            "worker_used": worker_name
        }
        
        if was_otp_verified and 'pending_input_text' in locals() and pending_input_text:
            result_dict["original_query"] = pending_input_text
            
        return result_dict

    def _prepare_worker_input(self, intent, original_input, session_id):
        base_input = {
            "user_id": original_input.get("user_id"),
            "session_id": session_id
        }
        
        if intent in ["policy_inquiry"]:
            base_input["query_type"] = "policy_number"
        elif intent in ["policy_period"]:
            base_input["query_type"] = "policy_period"
        elif intent in ["coverage_question", "faq", "personal_faq"]:
            base_input["query"] = original_input.get("user_input")
        elif intent in ["address_update", "phone_update", "email_update", "nominee_update", "complaint", "human_agent_request"]:
            base_input["issue_type"] = intent
        elif intent == "renewal":
            base_input["policy_id"] = original_input.get("policy_id")
        elif intent == "policy_cancellation":
            base_input["action"] = intent
            base_input["reference_id"] = original_input.get("policy_id")
        elif intent == "verify_otp":
            base_input["action"] = "verify_otp"
            base_input["otp"] = original_input.get("user_input").strip()
            
        return base_input
