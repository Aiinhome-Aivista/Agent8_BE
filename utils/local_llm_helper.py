import os
import json
import requests

def _chat(messages: list, *, model: str = None, max_tokens: int = 400, temperature: float = 0.7, json_mode: bool = False) -> dict:
    mode = os.getenv("LLM_MODE", "local").lower()
    
    # --- API MODE ---
    if mode == "api" and os.getenv("MISTRAL_API_KEY"):
        url = os.getenv("MISTRAL_API_URL", "https://api.mistral.ai/v1/chat/completions")
        api_key = os.getenv("MISTRAL_API_KEY")
        use_model = model or os.getenv("MISTRAL_MODEL", "mistral-small-latest")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": use_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
            
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            return response.json()  # Official API returns correct format
        except Exception as e:
            print(f"Error calling official Mistral API: {e}")
            return {"choices": [{"message": {"content": "{}"}}]}

    # --- LOCAL MODE ---
    else:
        endpoint = os.getenv("MISTRAL_ENDPOINT", "http://122.163.121.176:3038")
        use_model = model or "mistral:latest"
        
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt += f"{role.upper()}:\n{content}\n\n"

        url = f"{endpoint}/api/generate"
        payload = {
            "model": use_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        if json_mode:
            payload["format"] = "json"
            
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()
            return {
                "choices": [
                    {
                        "message": {
                            "content": data.get("response", "")
                        }
                    }
                ]
            }
        except Exception as e:
            print(f"Error calling local API ({url}): {e}")
            return {"choices": [{"message": {"content": "{}"}}]}

