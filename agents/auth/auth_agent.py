import random
from agents.base_agent import BaseAgent
from services.notification.notification_service import NotificationService
from services.memory.memory_service import MemoryService

class AuthAgent(BaseAgent):
    def __init__(self):
        super().__init__("AuthAgent")
        self.notification_service = NotificationService()
        self.memory_service = MemoryService()

    def execute(self, input_data):
        action = input_data.get("action")
        user_id = input_data.get("user_id")
        session_id = input_data.get("session_id")
        
        if action == "generate_otp":
            return self._generate_otp(user_id, session_id)
        elif action == "verify_otp":
            otp = input_data.get("otp")
            return self._verify_otp(session_id, otp)
        else:
            raise ValueError("Invalid action for AuthAgent")

    def _generate_otp(self, user_id, session_id):
        otp = str(random.randint(100000, 999999))
        
        # Store in session memory
        self.memory_service.update_session_memory(session_id, user_id, {"expected_otp": otp})
        
        # Queue notification (dummy recipient here, should fetch from DB)
        self.notification_service.queue_notification(
            user_id=user_id,
            channel="sms",
            recipient="user_phone",
            subject="Your OTP",
            body=f"Your OTP is {otp}"
        )
        
        return {"status": "OTP Generated and Sent"}

    def _verify_otp(self, session_id, provided_otp):
        context = self.memory_service.get_session_memory(session_id)
        expected_otp = context.get("expected_otp")
        
        if expected_otp and str(expected_otp) == str(provided_otp):
            self.memory_service.update_session_memory(session_id, context.get('user_id'), {"auth_status": "VERIFIED"})
            return {"status": "VERIFIED"}
        else:
            return {"status": "FAILED", "reason": "Invalid OTP"}
