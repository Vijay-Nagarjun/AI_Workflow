"""
Calls an OpenRouter chat model and returns plain text (no JSON parsing or
validation). Used for the email draft, which is free text, not structured
data -- kept separate from llm_json.py so that module stays purely about
schema-validated calls.
"""
from http_utils import post_json_with_retry

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def call_llm_text(*, api_key: str, model: str, system_prompt: str, user_prompt: str) -> str:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    data = post_json_with_retry(OPENROUTER_URL, json=payload, headers=headers, timeout=60)
    return data["choices"][0]["message"]["content"].strip()