import asyncio
from datetime import datetime, timedelta
from database.db import execute_query

async def run_memory_cleanup():
    while True:
        try:
            # Cleanup session_memory older than 24 hours
            cutoff = datetime.now() - timedelta(hours=24)
            query = "DELETE FROM session_memory WHERE updated_at < %s"
            execute_query(query, (cutoff,))
        except Exception as e:
            print(f"Error in Memory Cleanup: {e}")
            
        await asyncio.sleep(3600) # Run every hour
