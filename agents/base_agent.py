import time
from services.audit.audit_service import AuditService

class BaseAgent:
    def __init__(self, name):
        self.name = name
        self.audit_service = AuditService()

    def run(self, input_data, workflow_id=None):
        start_time = time.time()
        status = "SUCCESS"
        error = None
        output_data = None

        try:
            output_data = self.execute(input_data)
        except Exception as e:
            status = "FAILED"
            error = str(e)
            raise e
        finally:
            execution_time_ms = int((time.time() - start_time) * 1000)
            try:
                self.audit_service.log_agent_execution(
                    agent_name=self.name,
                    workflow_id=workflow_id,
                    input_data=input_data,
                    output_data=output_data,
                    execution_time_ms=execution_time_ms,
                    status=status,
                    error=error
                )
            except Exception as audit_err:
                print(f"[AuditService] Non-critical logging error for {self.name}: {audit_err}")
        
        return output_data

    def execute(self, input_data):
        raise NotImplementedError("Subclasses must implement the execute method")

