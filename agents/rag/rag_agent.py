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
        
        # Generate answer using LLM
        system_prompt = "You are a helpful insurance assistant. Answer the user's question accurately based ONLY on the provided context. Speak directly to the user in a natural, conversational tone. Do NOT use phrases like 'Based on the provided context' or 'According to the documents'. If the context does not contain the answer, say 'I cannot find this information.' Do not invent information."
        user_prompt = f"Context:\n{context[:4000]}\n\nQuestion:\n{user_query}"
        
        try:
            resp = _chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=300,
                temperature=0.1
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


