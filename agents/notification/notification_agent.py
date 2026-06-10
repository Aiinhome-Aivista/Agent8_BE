from agents.base_agent import BaseAgent
from services.notification.notification_service import NotificationService

class NotificationAgent(BaseAgent):
    def __init__(self):
        super().__init__("NotificationAgent")
        self.notification_service = NotificationService()

    def execute(self, input_data):
        user_id = input_data.get("user_id")
        channel = input_data.get("channel")
        recipient = input_data.get("recipient")
        subject = input_data.get("subject")
        body = input_data.get("body")
        
        self.notification_service.queue_notification(
            user_id=user_id,
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body
        )
        
        return {"status": "Notification Queued"}
