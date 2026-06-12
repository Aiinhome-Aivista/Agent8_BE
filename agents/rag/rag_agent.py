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
        
        # 1. Search Knowledge Base (company-wide documents uploaded by CSR)
        kb_results = search_kb_documents(user_query, top_k=5)
        
        # 2. Search user's personal documents
        personal_results = []
        if user_id:
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
        
        greeting_instruction = "Begin with a polite greeting (using the user's name if known)." if turn_count == 1 else "Do NOT greet the user or use their name, just answer the question directly to avoid repetition."

        # Generate answer using LLM
        system_prompt = f"You are a professional and helpful insurance assistant representing InsureAI. Answer the user's question accurately based ONLY on the provided context. Your tone must be strictly factual, objective, and professional. Do NOT use overly enthusiastic marketing language, fluff, or phrases like 'exciting features' or 'truly remarkable'. Present the core information using clear, well-structured bullet points so it is easy to read. {greeting_instruction} End by offering further assistance. Do NOT use phrases like 'Based on the provided context' or 'According to the documents'. If the context lacks the answer, politely apologize and state you cannot find it. Do not invent facts."
        user_prompt = f"Context:\n{context[:4000]}\n\nQuestion:\n{user_query}"
        
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
        except Exception as e:
            answer_text = f"Error generating response: {str(e)}"
        
        formatted_response = answer_text
        
        return {
            "response": formatted_response,
            "context_used": context[:2000],
            "sources": [f"chunk_{i}" for i in range(len(all_context))]
        }


