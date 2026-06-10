import asyncio
from services.notification.notification_service import NotificationService

async def run_notification_processor():
    notification_service = NotificationService()
    while True:
        try:
            # print("Running Notification Processor...")
            notification_service.process_queue()
        except Exception as e:
            print(f"Error in Notification Processor: {e}")
            
        await asyncio.sleep(10) # Run every 10 seconds
