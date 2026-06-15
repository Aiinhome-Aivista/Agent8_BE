from agents.base_agent import BaseAgent
from utils.kb_helper import search_kb_documents
from utils.rag_helper import search_documents
from utils.local_llm_helper import _chat
from services.memory.memory_service import MemoryService

import os
import re


class RAGAgent(BaseAgent):
    def __init__(self):
        super().__init__("RAGAgent")
        self.model = os.getenv("MISTRAL_MODEL", "")
        
        # Initialize CrossEncoder for reranking
        try:
            # pyrefly: ignore [missing-import]
            from sentence_transformers import CrossEncoder
            self.reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        except Exception as e:
            print(f"Warning: Could not load reranker: {e}")
            self.reranker = None

    def execute(self, input_data):
        user_query = input_data.get("query", "").strip()
        user_id = input_data.get("user_id")
        intent = input_data.get("intent")
        session_id = input_data.get("session_id")

        # --------------------------------------------------
        # Retrieve KB Documents
        # --------------------------------------------------
        kb_results = search_kb_documents(
            user_query,
            top_k=15
        )

        # --------------------------------------------------
        # Retrieve Personal Documents
        # --------------------------------------------------
        personal_results = []

        if user_id and intent in ["personal_faq", "profile_summary"]:
            try:
                personal_results = search_documents(
                    user_id,
                    user_query,
                    top_k=15
                )
            except Exception:
                personal_results = []

        # --------------------------------------------------
        # Merge Results
        # --------------------------------------------------
        all_context = []
        chunk_source_map = {}

        if personal_results:
            for c in personal_results:
                all_context.append(c)
                chunk_source_map[c] = True

        if kb_results:
            for c in kb_results:
                all_context.append(c)
                if c not in chunk_source_map:
                    chunk_source_map[c] = False

        # --------------------------------------------------
        # No Results Found
        # --------------------------------------------------
        if not all_context:
            return {
                "response": (
                    "I couldn't find any relevant information "
                    "in the available documents."
                ),
                "context_used": "",
                "sources": []
            }

        # --------------------------------------------------
        # Remove Duplicate Chunks
        # --------------------------------------------------
        unique_context = []
        seen = set()

        for chunk in all_context:
            chunk_text = str(chunk).strip()

            if chunk_text and chunk_text not in seen:
                seen.add(chunk_text)
                unique_context.append(chunk_text)

        all_context = unique_context

        # --------------------------------------------------
        # Rerank Context Chunks
        # --------------------------------------------------
        if getattr(self, 'reranker', None) and all_context:
            try:
                pairs = [[user_query, chunk] for chunk in all_context]
                scores = self.reranker.predict(pairs)
                
                # Boost personal documents for personal queries
                personal_keywords = ["my", "mine", "policy", "insured", "premium", "nominee", "bill", "claim", "profile", "summary"]
                is_personal_query = any(w in user_query.lower().split() for w in personal_keywords)
                
                scored_chunks = []
                for chunk, score in zip(all_context, scores):
                    is_personal = chunk_source_map.get(chunk, False)
                    if is_personal_query and is_personal:
                        score += 10.0 # massive boost to ensure personal docs outrank brochure
                    scored_chunks.append((score, chunk))
                
                # Sort descending
                scored_chunks.sort(key=lambda x: x[0], reverse=True)
                
                # Keep top 5 most relevant chunks
                all_context = [chunk for score, chunk in scored_chunks[:5]]
            except Exception as e:
                print(f"Reranking failed: {e}")
                all_context = all_context[:5]
        else:
            all_context = all_context[:5]

        print("\n======================")
        print("QUERY:", user_query)
        print("======================")

        for i, chunk in enumerate(all_context):
            print(f"\n----- CHUNK {i+1} -----")
            print(chunk)

        # --------------------------------------------------
        # Format Context
        # --------------------------------------------------
        formatted_chunks = []

        for idx, chunk in enumerate(all_context):
            formatted_chunks.append(
                f"DOCUMENT CHUNK {idx + 1}:\n{chunk}"
            )

        context = "\n\n".join(formatted_chunks)

        # --------------------------------------------------
        # Session Memory
        # --------------------------------------------------
        mem = (
            MemoryService().get_session_memory(session_id)
            if session_id
            else {}
        )

        turn_count = mem.get("turn_count", 1)

        greeting_instruction = (
            "Start with a short greeting."
            if turn_count == 1
            else "Do not greet the user again."
        )

        # --------------------------------------------------
        # Detect Factual Questions
        # --------------------------------------------------
        factual_keywords = [
            "maximum",
            "minimum",
            "entry age",
            "age",
            "policy term",
            "sum insured",
            "waiting period",
            "coverage",
            "covered",
            "what is",
            "does",
            "how much",
            "eligible",
            "limit"
        ]

        factual_mode = any(
            keyword in user_query.lower()
            for keyword in factual_keywords
        )

        if factual_mode:
            answer_style = """
This is a factual lookup question.

Answer directly in 1-3 sentences.

Do not use marketing language.

Do not add unnecessary explanation.
"""
        else:
            answer_style = """
Use bullet points when appropriate.

Keep the answer concise, professional, and easy to read.
"""

        # --------------------------------------------------
        # System Prompt
        # --------------------------------------------------
        system_prompt = f"""
You are InsureAI, a professional insurance assistant.

{greeting_instruction}

STRICT RULES:

1. Answer ONLY using the provided context.

2. NEVER guess.

3. NEVER invent facts.

4. NEVER infer information that is not explicitly stated.

5. If the answer is not clearly present in the context, respond exactly:

"I couldn't find that information in the available documents."

6. If multiple values exist, use ONLY the value directly related to the user's question.

7. Do NOT confuse different cover types.

Example:
- Hospitalization Cover Maximum Entry Age = No Limit
- Personal Accident Cover Maximum Entry Age = 65 Years

Use the correct value based on the user's question.

8. Do NOT mention:
   - document names
   - file names
   - brochure names

9. Do NOT say:
   - "According to the document"
   - "Based on the brochure"
   - "The uploaded PDF says"

10. Accuracy is more important than sounding helpful.

11. Never over-promise benefits.

12. Mention conditions or eligibility requirements whenever they appear in the context.

13. Do NOT apply conditions or footnotes from one benefit to another benefit.

14. A condition must ONLY be mentioned if it is explicitly tied to the exact benefit being discussed.

15. If the user asks whether a condition applies to a benefit:
- Check whether the condition is explicitly attached to that exact benefit.
- If the condition belongs to another benefit, answer: "No, that condition applies to [Correct Benefit], not [Requested Benefit]."
- Never transfer footnotes, conditions, waiting periods, age limits, or eligibility criteria from one benefit to another.

16. Use markdown formatting.

STYLE:

- Professional
- Friendly
- Natural

{answer_style}

End with:
"Please let me know if you need any further assistance."
"""

        # --------------------------------------------------
        # User Prompt
        # --------------------------------------------------
        user_prompt = f"""
CONTEXT:

{context[:5000]}

QUESTION:

{user_query}
"""

        # --------------------------------------------------
        # Generate Response
        # --------------------------------------------------
        try:
            resp = _chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                max_tokens=500,
                temperature=0.0
            )

            answer_text = (
                resp["choices"][0]["message"]["content"]
                .strip()
            )

            # Remove source tags generated by LLM
            answer_text = re.sub(
                r"\[Source:\s*.+?\]",
                "",
                answer_text
            ).strip()

            # Extract source tags from context
            sources = list(
                set(
                    re.findall(
                        r"\[Source:\s*(.+?)\]",
                        context
                    )
                )
            )

            if sources:
                source_tags = " ".join(
                    [
                        f"[Source: {source}]"
                        for source in sources
                    ]
                )

                answer_text += f"\n\n{source_tags}"

        except Exception as e:
            answer_text = (
                f"Error generating response: {str(e)}"
            )

        return {
            "response": answer_text,
            "context_used": context[:2000],
            "sources": [
                f"chunk_{i}"
                for i in range(len(all_context))
            ]
        }