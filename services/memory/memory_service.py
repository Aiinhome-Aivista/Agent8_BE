import json
from datetime import datetime
from database.db_utils import execute_query, fetch_one, fetch_all

class MemoryService:
    def __init__(self):
        pass

    def get_customer_preferences(self, user_id):
        query = "SELECT preferred_language, preferred_channel FROM customer_preferences WHERE user_id = %s"
        return fetch_one(query, (user_id,))

    def update_customer_preferences(self, user_id, preferred_language=None, preferred_channel=None):
        existing = self.get_customer_preferences(user_id)
        if existing:
            query = """
                UPDATE customer_preferences 
                SET preferred_language = COALESCE(%s, preferred_language), 
                    preferred_channel = COALESCE(%s, preferred_channel), 
                    updated_at = %s 
                WHERE user_id = %s
            """
            execute_query(query, (preferred_language, preferred_channel, datetime.now(), user_id))
        else:
            query = """
                INSERT INTO customer_preferences (user_id, preferred_language, preferred_channel) 
                VALUES (%s, %s, %s)
            """
            execute_query(query, (user_id, preferred_language, preferred_channel))

    def get_session_memory(self, session_id):
        query = "SELECT context_data FROM session_memory WHERE session_id = %s"
        result = fetch_one(query, (session_id,))
        if result and result.get('context_data'):
            return result['context_data']
        return {}

    def update_session_memory(self, session_id, user_id, context_data):
        existing = self.get_session_memory(session_id)
        if existing:
            # Merge context_data
            merged = {**existing, **context_data}
            query = "UPDATE session_memory SET context_data = %s, updated_at = %s WHERE session_id = %s"
            execute_query(query, (json.dumps(merged), datetime.now(), session_id))
        else:
            query = "INSERT INTO session_memory (session_id, user_id, context_data) VALUES (%s, %s, %s)"
            execute_query(query, (session_id, user_id, json.dumps(context_data)))

    def log_episodic_event(self, user_id, event_type, event_summary):
        query = "INSERT INTO episodic_memory (user_id, event_type, event_summary) VALUES (%s, %s, %s)"
        execute_query(query, (user_id, event_type, event_summary))

    def get_episodic_events(self, user_id, limit=5):
        query = "SELECT event_type, event_summary, created_at FROM episodic_memory WHERE user_id = %s ORDER BY created_at DESC LIMIT %s"
        return fetch_all(query, (user_id, limit))
