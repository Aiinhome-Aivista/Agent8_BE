from agents.base_agent import BaseAgent
from services.document.document_service import DocumentService

class DocumentAgent(BaseAgent):
    def __init__(self):
        super().__init__("DocumentAgent")
        self.document_service = DocumentService()

    def execute(self, input_data):
        document_type = input_data.get("document_type") # e.g., 'Policy Summary PDF', 'Renewal Certificate PDF'
        reference_id = input_data.get("reference_id")
        content_data = input_data.get("content_data", {})
        
        file_path = self.document_service.generate_pdf(
            document_type=document_type,
            reference_id=reference_id,
            content_data=content_data
        )
        
        return {
            "status": "Document Generated",
            "file_path": file_path
        }
