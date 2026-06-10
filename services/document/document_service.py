import os
import json
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from database.db import execute_query

class DocumentService:
    def __init__(self):
        self.output_dir = r"d:\Agent-8\Agent8_BE\uploads\generated_documents"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def generate_pdf(self, document_type, reference_id, content_data):
        file_name = f"{document_type}_{reference_id}_{int(datetime.now().timestamp())}.pdf"
        file_path = os.path.join(self.output_dir, file_name)

        # Generate basic PDF
        c = canvas.Canvas(file_path, pagesize=letter)
        c.drawString(100, 750, f"Document Type: {document_type}")
        c.drawString(100, 730, f"Reference ID: {reference_id}")
        
        y_position = 700
        for key, value in content_data.items():
            c.drawString(100, y_position, f"{key}: {value}")
            y_position -= 20
            
        c.save()

        # Log into generated_documents table
        query = """
            INSERT INTO generated_documents (document_type, reference_id, file_path, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        result = execute_query(query, (document_type, reference_id, file_path, json.dumps(content_data), datetime.now()))
        
        return file_path
