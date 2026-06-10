import json
from datetime import datetime
from database.db import execute_query

class AuditService:
    def __init__(self):
        pass

    def log_agent_execution(self, agent_name, workflow_id, input_data, output_data, execution_time_ms, status, error=None):
        query = """
            INSERT INTO agent_executions (agent_name, workflow_id, input_data, output_data, execution_time_ms, status, error, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        execute_query(query, (
            agent_name, 
            workflow_id, 
            json.dumps(input_data) if input_data else None, 
            json.dumps(output_data) if output_data else None, 
            execution_time_ms, 
            status, 
            error, 
            datetime.now()
        ))

    def log_audit_event(self, user_id, event_type, details):
        query = """
            INSERT INTO audit_logs (user_id, event_type, details, created_at)
            VALUES (%s, %s, %s, %s)
        """
        execute_query(query, (user_id, event_type, json.dumps(details) if isinstance(details, dict) else details, datetime.now()))

    def log_system_health(self, component_name, status, details):
        query = """
            INSERT INTO system_health_logs (component_name, status, details, recorded_at)
            VALUES (%s, %s, %s, %s)
        """
        execute_query(query, (component_name, status, json.dumps(details) if isinstance(details, dict) else details, datetime.now()))

    def log_agent_metric(self, agent_name, metric_name, metric_value):
        query = """
            INSERT INTO agent_metrics (agent_name, metric_name, metric_value, recorded_at)
            VALUES (%s, %s, %s, %s)
        """
        execute_query(query, (agent_name, metric_name, metric_value, datetime.now()))
