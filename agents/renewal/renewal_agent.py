from agents.base_agent import BaseAgent
from services.notification.notification_service import NotificationService
from database.db_utils import execute_query

class RenewalAgent(BaseAgent):
    def __init__(self):
        super().__init__("RenewalAgent")
        self.notification_service = NotificationService()

    def execute(self, input_data):
        user_id = input_data.get("user_id")
        policy_id = input_data.get("policy_id")
        
        # Simulate payment validation and renewal
        # Assume payment is validated
        
        query = """
            UPDATE policies SET status = 'RENEWED', updated_at = NOW() WHERE id = %s AND user_id = %s
        """
        execute_query(query, (policy_id, user_id))
        
        # Log renewal record
        renew_query = """
            INSERT INTO renewals (policy_id, user_id, renewal_date, status)
            VALUES (%s, %s, NOW(), 'COMPLETED')
        """
        execute_query(renew_query, (policy_id, user_id))
        
        # Queue notification
        self.notification_service.queue_notification(
            user_id=user_id,
            channel="email",
            recipient="user@example.com", # placeholder
            subject="Policy Renewed Successfully",
            body=f"Your policy {policy_id} has been successfully renewed."
        )
        
        return {
            "status": "Success",
            "message": "Policy renewed and confirmation notification sent."
        }
