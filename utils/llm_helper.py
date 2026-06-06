import os
import json
from .local_llm_helper import _chat

INSURANCE_SYSTEM_PROMPT = """You are InsureAI Assistant, an expert AI-powered insurance virtual agent.

RULES:
1. Keep responses VERY short and direct (1-2 sentences maximum).
2. Do not use long generic introductory paragraphs or ask to verify identity unprompted.
3. If the user asks a question about policies, coverage, or rules, you MUST answer ONLY based on the provided "POLICY DOCUMENTS AND COMPANY KNOWLEDGE BASE".
4. If the context says "[No relevant documents found for this query.]" or if the answer isn't in the provided text, you MUST clearly state: "I couldn't find any specific information regarding this in your uploaded policies or our knowledge base." Do NOT invent or hallucinate answers.
5. If the user asks to update their mobile number, email, or address, instruct them to go to the "Raise Ticket" section to submit an update request and provide a valid reason for the change.
6. Format monetary amounts in Indian Rupees (₹).
7. Never share or ask for full PAN, Aadhaar or bank account numbers.
8. Show empathy for complaints before offering solutions.
9. If uncertain, offer to escalate to a human agent.
"""

INTENT_LABELS = [
    "policy_inquiry", "renewal", "address_update", "contact_update",
    "premium_query", "complaint", "escalation_request", "faq", "coverage_question"
]

def _prepare_intent_prompt(message: str) -> list:
    system = (
        "Classify this insurance customer message into exactly ONE of these intents:\n"
        + ", ".join(INTENT_LABELS)
        + "\nRespond ONLY with valid JSON like: {\"intent\": \"renewal\", \"confidence\": 0.94}\nConfidence must be a float between 0 and 1."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": message}]

def detect_intent(message: str) -> dict:
    """Classify user message into one of the predefined intents.
    Returns a dict like {"intent": str, "confidence": float}.
    """
    try:
        resp = _chat(model="mistral:latest", messages=_prepare_intent_prompt(message), max_tokens=60, temperature=0, json_mode=True)
        content = resp["choices"][0]["message"]["content"].strip()
        # Clean possible markdown fences
        content = content.replace("```json", "").replace("```", "").strip()
        result = json.loads(content)
        if result.get("intent") not in INTENT_LABELS:
            result["intent"] = "faq"
        return result
    except Exception:
        # Simple keyword fallback (same as previous implementation)
        lower = message.lower()
        if any(w in lower for w in ["renew", "renewal", "expire"]):
            return {"intent": "renewal", "confidence": 0.82}
        if any(w in lower for w in ["address", "moved", "location"]):
            return {"intent": "address_update", "confidence": 0.78}
        if any(w in lower for w in ["complaint", "angry", "wrong", "problem", "frustrated"]):
            return {"intent": "complaint", "confidence": 0.80}
        if any(w in lower for w in ["premium", "amount", "cost", "price"]):
            return {"intent": "premium_query", "confidence": 0.76}
        if any(w in lower for w in ["cover", "coverage", "include", "protect"]):
            return {"intent": "coverage_question", "confidence": 0.75}
        if any(w in lower for w in ["escalate", "human", "agent", "manager"]):
            return {"intent": "escalation_request", "confidence": 0.90}
        return {"intent": "faq", "confidence": 0.60}

def generate_chat_response(user_message: str, conversation_history: list, customer_context: str = "") -> str:
    """Generate a response using the local LLM.
    conversation_history is a list of dicts {"role": "user"|"assistant", "content": str}.
    """
    system = INSURANCE_SYSTEM_PROMPT
    if customer_context:
        system += f"\n\nCUSTOMER CONTEXT:\n{customer_context}"
    messages = [{"role": "system", "content": system}]
    messages.extend(conversation_history[-10:])
    messages.append({"role": "user", "content": user_message})
    resp = _chat(model="mistral:latest", messages=messages, max_tokens=400, temperature=0.7)
    return resp["choices"][0]["message"]["content"].strip()

def summarize_conversation(messages: list) -> str:
    """Summarize a conversation for escalation handoff."""
    if not messages:
        return "No conversation history."
    history_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages[-20:]])
    system = (
        "Summarize this insurance customer support conversation in 3-4 bullet points. "
        "Focus on: customer's issue, what was tried, why escalation is needed."
    )
    resp = _chat(model="mistral:latest", messages=[{"role": "system", "content": system}, {"role": "user", "content": history_text}], max_tokens=200, temperature=0)
    return resp["choices"][0]["message"]["content"].strip()

def answer_rag_question(question: str, context_chunks: list) -> str:
    """Answer a question using retrieved document chunks (RAG)."""
    if not context_chunks:
        return "No relevant document content found. Please upload your policy documents first."
    context = "\n\n---\n\n".join(context_chunks[:5])
    system = (
        "You are an insurance policy expert. Answer the question using ONLY the provided policy document excerpts. "
        "If the answer isn't in the documents, say so clearly. Be specific and cite relevant details."
    )
    resp = _chat(model="mistral:latest", messages=[{"role": "system", "content": system}, {"role": "user", "content": f"POLICY DOCUMENTS:\n{context}\n\nQUESTION: {question}"}], max_tokens=350, temperature=0)
    return resp["choices"][0]["message"]["content"].strip()
