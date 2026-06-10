from datetime import datetime
from database.db import execute_query, fetch_all

class NotificationService:
    def __init__(self):
        pass

    def queue_notification(self, user_id, channel, recipient, subject, body):
        query = """
            INSERT INTO notification_queue (user_id, channel, recipient, subject, body, status, created_at)
            VALUES (%s, %s, %s, %s, %s, 'QUEUED', %s)
        """
        execute_query(query, (user_id, channel, recipient, subject, body, datetime.now()))

    def process_queue(self):
        # Fetch pending notifications
        query = "SELECT id, channel, recipient, subject, body FROM notification_queue WHERE status = 'QUEUED' AND retry_count < 3"
        pending = fetch_all(query)
        
        for notif in pending:
            try:
                if notif['channel'] == 'email':
                    self._send_email(notif['recipient'], notif['subject'], notif['body'])
                elif notif['channel'] == 'sms':
                    self._send_sms(notif['recipient'], notif['body'])
                elif notif['channel'] == 'whatsapp':
                    self._send_whatsapp(notif['recipient'], notif['body'])
                elif notif['channel'] == 'in-app':
                    self._send_in_app(notif['recipient'], notif['body'])
                
                # Mark as sent
                self._update_status(notif['id'], 'SENT')
            except Exception as e:
                # Increment retry count
                self._handle_failure(notif['id'])
                print(f"Failed to send notification {notif['id']}: {e}")

    def _send_email(self, recipient, subject, body):
        # Placeholder for actual email sending logic (e.g. SMTP, SendGrid)
        print(f"Sending Email to {recipient} - {subject}")

    def _send_sms(self, recipient, body):
        # Placeholder for SMS logic (e.g. Twilio)
        print(f"Sending SMS to {recipient}")

    def _send_whatsapp(self, recipient, body):
        # Placeholder for WhatsApp logic
        print(f"Sending WhatsApp to {recipient}")

    def _send_in_app(self, recipient, body):
        # Placeholder for In-App notification logic (e.g. WebSockets / DB flag)
        print(f"Sending In-App Notification to {recipient}")

    def _update_status(self, notif_id, status):
        query = "UPDATE notification_queue SET status = %s, sent_at = %s WHERE id = %s"
        execute_query(query, (status, datetime.now(), notif_id))

    def _handle_failure(self, notif_id):
        query = "UPDATE notification_queue SET retry_count = retry_count + 1 WHERE id = %s"
        execute_query(query, (notif_id,))
