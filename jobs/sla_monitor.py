import asyncio
from services.sla.sla_service import SLAService

async def run_sla_monitor():
    sla_service = SLAService()
    while True:
        try:
            # print("Running SLA Monitor...")
            sla_service.check_breaches()
        except Exception as e:
            print(f"Error in SLA Monitor: {e}")
        
        await asyncio.sleep(60) # Run every minute
