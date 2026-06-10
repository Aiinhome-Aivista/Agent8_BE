from agents.base_agent import BaseAgent
from services.rag.rag_service import RAGService

class RAGAgent(BaseAgent):
    def __init__(self):
        super().__init__("RAGAgent")
        self.rag_service = RAGService()

    def execute(self, input_data):
        user_query = input_data.get("query")
        
        # Retrieve context from vector store
        results = self.rag_service.search_documents(user_query, top_k=5, similarity_threshold=0.75)
        
        if not results:
            return {"response": "I do not have that information in my knowledge base."}
            
        context = " ".join([res["document"] for res in results])
        
        # Simulated LLM generation (In production, pass context + user_query to LLM)
        # We will format the output strictly as per the Enterprise Citation Flow
        
        answer_text = f"Based on the policy documents, here is the information regarding '{user_query}'."
        
        # Format Top 5 Chunks
        chunks_text = "\n".join([f"- Chunk {i+1}: {res['document'][:150]}..." for i, res in enumerate(results)])
        
        # Format Source References
        sources_text = ", ".join([str(res["metadata"].get("document_id", "Unknown")) for res in results])
        
        formatted_response = (
            f"**Answer:**\n{answer_text}\n\n"
            f"**Top Chunks Retrieved:**\n{chunks_text}\n\n"
            f"**Source References:** {sources_text}"
        )
        
        return {
            "response": formatted_response,
            "context_used": context,
            "sources": [res["metadata"].get("document_id") for res in results]
        }
