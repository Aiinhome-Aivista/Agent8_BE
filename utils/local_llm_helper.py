import os
import json
import requests

def _chat(messages: list, *, model: str = "mistral:latest", max_tokens: int = 400, temperature: float = 0.7, json_mode: bool = False) -> dict:
    """Send a chat completion request to a locally‑hosted Mistral server.

    The function mirrors the response shape of OpenAI's ``client.chat.completions.create``
    so the rest of the codebase can remain unchanged.

    Args:
        messages: List of dicts with ``role`` ("system"|"user"|"assistant") and ``content``.
        model: The model identifier – defaults to ``mistral:latest``.
        max_tokens: Maximum number of tokens to generate.
        temperature: Sampling temperature.

    Returns:
        The JSON payload returned by the Mistral server (typically containing a ``choices``
        array with ``message.content``).
    """
    # Determine the active provider
    provider = os.getenv("ACTIVE_LLM_PROVIDER", "mistral_cloud").lower()

    if provider == "ollama":
        endpoint = os.getenv("MISTRAL_ENDPOINT")
        local_model = os.getenv("OLLAMA_MODEL", "mistral:latest")
        
        if not endpoint:
            raise RuntimeError("MISTRAL_ENDPOINT is required when ACTIVE_LLM_PROVIDER is 'ollama'")

        # ─── Local Ollama / Mistral Setup ───
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt += f"{role.upper()}:\n{content}\n\n"

        url = f"{endpoint}/api/generate"
        payload = {
            "model": local_model,  # Override model parameter with env setting
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
            print(f"Error calling local LLM ({url}): {e}")
            return {"choices": [{"message": {"content": "{}"}}]}
    
    elif provider == "mistral_cloud":
        api_key = os.getenv("MISTRAL_API_KEY")
        api_url = os.getenv("MISTRAL_API_URL", "https://api.mistral.ai/v1/chat/completions")
        cloud_model = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
        
        if not api_key:
            raise RuntimeError("MISTRAL_API_KEY is required when ACTIVE_LLM_PROVIDER is 'mistral_cloud'")

        # ─── Mistral Cloud API Setup ───
        payload = {
            "model": cloud_model,  # Override model parameter with env setting
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            print(f"Error calling Mistral API {api_url}: {e}")
            return {"choices": [{"message": {"content": "{}"}}]}
            
    else:
        raise RuntimeError(f"Unknown ACTIVE_LLM_PROVIDER: '{provider}'. Please use 'ollama' or 'mistral_cloud'.")
