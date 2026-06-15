from agents.base_agent import BaseAgent
from utils.kb_helper import search_kb_documents
from utils.rag_helper import search_documents
from utils.local_llm_helper import _chat
import os

class RAGAgent(BaseAgent):
    def __init__(self):
        super().__init__("RAGAgent")
        self.model = os.getenv("MISTRAL_MODEL", "")

    def execute(self, input_data):
        user_query = input_data.get("query")
        user_id = input_data.get("user_id")
        intent = input_data.get("intent")
        
        # 1. Search Knowledge Base (company-wide documents uploaded by CSR)
        kb_results = search_kb_documents(user_query, top_k=5)
        
        # 2. Search user's personal documents
        personal_results = []
        if user_id and intent == "personal_faq":
            try:
                personal_results = search_documents(user_id, user_query, top_k=5)
            except Exception:
                personal_results = []
        
        # Combine results
        all_context = []
        if personal_results:
            all_context.extend(personal_results)
        if kb_results:
            all_context.extend(kb_results)
        
        if not all_context:
            return {"response": "I do not have that information in my knowledge base. Please upload relevant documents first."}
            
        context = " ".join([c if isinstance(c, str) else str(c) for c in all_context])
        
        # Fetch session memory to know if it's the first turn
        from services.memory.memory_service import MemoryService
        session_id = input_data.get("session_id")
        mem = MemoryService().get_session_memory(session_id) if session_id else {}
        turn_count = mem.get("turn_count", 1)
        
        greeting_instruction = "Begin with a polite greeting." if turn_count == 1 else "Do NOT greet the user again."

        # Generate answer using LLM
        system_prompt = f"You are a professional and helpful insurance assistant representing InsureAI. Answer the user's question accurately in a natural, conversational manner based ONLY on the provided context. Your tone must be friendly yet professional. Do not just output a raw bulleted list—always introduce your answer with a natural conversational sentence. Use markdown formatting to make your response look highly professional. Specifically, **bold** the key terms or titles in your bullet points. CRITICAL: When describing features, do NOT over-generalize or over-promise. You must accurately reflect conditions or caveats. For example: Do NOT list 'Medical Inflation Protection' as a separate feature; instead, combine it as '- **5-Year Tenure Option:** Provides long-term coverage and helps protect against the impact of medical inflation.' For 'Endless Sum Insured', use the wording '- **Endless Sum Insured:** Provides a once-in-a-lifetime hospitalization claim without any base sum insured limit, subject to policy terms and eligibility.' Do not summarize away important limitations. Structure the core information clearly. {greeting_instruction} End by offering further assistance. IMPORTANT: Do NOT mention document names or use phrases like 'Based on the document...' in your sentences. If the context lacks the answer, politely apologize and state you cannot find it. Do not invent facts."
        user_prompt = f"Context:\n{context[:4000]}\n\nQuestion:\n{user_query}"
        
        import re
        try:
            resp = _chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            answer_text = resp["choices"][0]["message"]["content"].strip()
            
            # Programmatically append source tags so the UI badge always renders
            sources = list(set(re.findall(r"\[Source:\s*(.+?)\]", context)))
            if sources:
                source_tags = " ".join([f"[Source: {s}]" for s in sources])
                # Remove any tags the LLM might have output on its own to prevent duplicates
                answer_text = re.sub(r"\[Source:\s*.+?\]", "", answer_text).strip()
                answer_text = f"{answer_text}\n\n{source_tags}"
        except Exception as e:
            answer_text = f"Error generating response: {str(e)}"
        
        formatted_response = answer_text
        
        return {
            "response": formatted_response,
            "context_used": context[:2000],
            "sources": [f"chunk_{i}" for i in range(len(all_context))]
        }


