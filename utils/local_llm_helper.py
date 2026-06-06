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
    endpoint = os.getenv("MISTRAL_ENDPOINT")
    if not endpoint:
        raise RuntimeError("MISTRAL_ENDPOINT environment variable is not set")

    # Combine messages into a single prompt string for /api/generate
    prompt = ""
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        prompt += f"{role.upper()}:\n{content}\n\n"

    # Some Ollama models prefer just the model name, e.g. 'mistral' instead of 'mistral:latest'
    # but we'll pass whatever is given.
    url = f"{endpoint}/api/generate"
    payload = {
        "model": model,
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
        
        # Mirror OpenAI response format so rest of codebase works unchanged
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
        print(f"Error calling {url}: {e}")
        # fallback format if error
        return {"choices": [{"message": {"content": "{}"}}]}
