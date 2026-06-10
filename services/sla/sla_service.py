from datetime import datetime, timedelta
from database.db_utils import execute_query, fetch_one, fetch_all

class SLAService:
    def __init__(self):
        pass

    def track_entity(self, entity_type, entity_id, rule_name):
        # Fetch SLA rule
        rule_query = "SELECT id, max_duration_minutes FROM sla_rules WHERE rule_name = %s"
        rule = fetch_one(rule_query, (rule_name,))
        if not rule:
            raise ValueError(f"SLA Rule {rule_name} not found")
        
        deadline = datetime.now() + timedelta(minutes=rule['max_duration_minutes'])
        
        insert_query = """
            INSERT INTO sla_tracking (entity_type, entity_id, rule_id, deadline, status)
            VALUES (%s, %s, %s, %s, 'ACTIVE')
        """
        execute_query(insert_query, (entity_type, entity_id, rule['id'], deadline))

    def update_status(self, tracking_id, status):
        query = "UPDATE sla_tracking SET status = %s, updated_at = %s WHERE id = %s"
        execute_query(query, (status, datetime.now(), tracking_id))

    def check_breaches(self):
        query = """
            SELECT st.id, st.entity_type, st.entity_id, sr.escalation_level 
            FROM sla_tracking st
            JOIN sla_rules sr ON st.rule_id = sr.id
            WHERE st.status = 'ACTIVE' AND st.deadline < %s
        """
        breached = fetch_all(query, (datetime.now(),))
        
        for record in breached:
            # Mark as breached
            self.update_status(record['id'], 'BREACHED')
            # Handle escalation based on record['escalation_level']
            # e.g., create an escalation log or notify supervisor
            print(f"SLA BREACH: Entity {record['entity_type']} (ID: {record['entity_id']}) escalated to {record['escalation_level']}")
