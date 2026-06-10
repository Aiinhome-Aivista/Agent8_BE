from datetime import datetime
from database.db import execute_query

class ApprovalService:
    def __init__(self):
        pass

    def create_approval_request(self, request_type, reference_id, requested_by):
        query = """
            INSERT INTO approval_requests (request_type, reference_id, requested_by, status, created_at)
            VALUES (%s, %s, %s, 'PENDING', %s)
            RETURNING id
        """
        result = execute_query(query, (request_type, reference_id, requested_by, datetime.now()))
        return result[0]['id'] if result else None

    def approve_request(self, request_id, action_by, comments=None):
        self._update_request_status(request_id, 'APPROVED', action_by, comments)

    def reject_request(self, request_id, action_by, comments=None):
        self._update_request_status(request_id, 'REJECTED', action_by, comments)

    def _update_request_status(self, request_id, status, action_by, comments):
        update_query = "UPDATE approval_requests SET status = %s, updated_at = %s WHERE id = %s"
        execute_query(update_query, (status, datetime.now(), request_id))

        history_query = """
            INSERT INTO approval_history (approval_request_id, action_taken, action_by, comments, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """
        execute_query(history_query, (request_id, status, action_by, comments, datetime.now()))
