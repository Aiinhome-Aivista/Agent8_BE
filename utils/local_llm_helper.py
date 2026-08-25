import os
import json
import requests

def _chat(messages: list, *, model: str = None, max_tokens: int = 400, temperature: float = 0.7, json_mode: bool = False) -> dict:
    mode = os.getenv("LLM_MODE", "local").lower()
    timeout = int(os.getenv("LLM_TIMEOUT", "300"))
    api_url = os.getenv("LLM_API_URL")
    
    # --- API MODE (Official Mistral Cloud API using API Key) ---
    if mode == "api" and os.getenv("MISTRAL_API_KEY") and not api_url:
        url = os.getenv("MISTRAL_API_URL", "https://api.mistral.ai/v1/chat/completions")
        api_key = os.getenv("MISTRAL_API_KEY")
        use_model = model or os.getenv("LLM_MODEL") or os.getenv("MISTRAL_MODEL", "mistral-small-latest")
        
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
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json()  # Official API returns correct format
        except Exception as e:
            error_details = response.text if 'response' in locals() else str(e)
            print(f"Error calling official Mistral API: {e} - Details: {error_details}")
            return {"choices": [{"message": {"content": "{}"}}]}

    # --- LOCAL / CUSTOM ENDPOINT MODE (e.g. Ollama generate endpoint) ---
    else:
        if api_url:
            url = api_url
        else:
            endpoint = os.getenv("MISTRAL_ENDPOINT", "http://122.163.121.176:3041")
            url = f"{endpoint.rstrip('/')}/api/generate"
            
        use_model = model or os.getenv("LLM_MODEL") or os.getenv("MISTRAL_MODEL", "mistral-small:24b")
        
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt += f"{role.upper()}:\n{content}\n\n"

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
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
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

