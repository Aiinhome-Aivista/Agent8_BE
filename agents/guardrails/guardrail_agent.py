import re
from agents.base_agent import BaseAgent

try:
    from presidio_analyzer import AnalyzerEngine  # pyrefly: ignore [missing-import]
    from presidio_anonymizer import AnonymizerEngine  # pyrefly: ignore [missing-import]
    HAS_PRESIDIO = True
except ImportError:
    HAS_PRESIDIO = False

class GuardrailAgent(BaseAgent):
    def __init__(self):
        super().__init__("GuardrailAgent")
        if HAS_PRESIDIO:
            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
            
        # Basic regex fallback for PAN, AADHAAR, PHONE, EMAIL
        self.regex_patterns = {
            "PHONE": r"\b\d{10}\b",
            "PAN": r"[A-Z]{5}[0-9]{4}[A-Z]{1}",
            "AADHAAR": r"\b\d{4}\s\d{4}\s\d{4}\b",
            "POLICY_NUMBER": r"\bPOL-\d{6}\b" # Example structure
        }

    def execute(self, input_data):
        text = input_data.get("text", "")
        mode = input_data.get("mode", "output") # input or output
        
        if mode == "input":
            return self._check_input_guardrails(text)
        elif mode == "output":
            return self._mask_pii(text)
        
    def _check_input_guardrails(self, text):
        # Basic Prompt Injection / Profanity Check
        lower_text = text.lower()
        if "ignore all previous instructions" in lower_text or "system prompt" in lower_text:
            return {"status": "BLOCKED", "reason": "Potential Prompt Injection Detected"}
            
        return {"status": "PASSED"}

    def _mask_pii(self, text):
        masked_text = text
        
        if HAS_PRESIDIO:
            results = self.analyzer.analyze(text=masked_text, entities=["PHONE_NUMBER", "US_SSN"], language='en')
            anonymized = self.anonymizer.anonymize(text=masked_text, analyzer_results=results)
            masked_text = anonymized.text
            
        # Fallback to Regex for specific Indian patterns and others
        for entity_type, pattern in self.regex_patterns.items():
            masked_text = re.sub(pattern, f"[{entity_type}_MASKED]", masked_text)
            
        return {"masked_text": masked_text}
