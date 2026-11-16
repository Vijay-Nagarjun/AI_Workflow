"""
Calls an OpenRouter chat model expecting strict JSON back, parses it, and
validates it against a pydantic schema. If the JSON is malformed or
doesn't match the expected shape, the validation error is fed back to the
model and it's asked again -- instead of crashing on the first bad
response (which is all the original code did: catch, print, raise).
"""
import json as json_lib
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from http_utils import post_json_with_retry

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

T = TypeVar("T", bound=BaseModel)


class LlmJsonFailed(RuntimeError):
    pass


def call_llm_json(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    schema: Type[T],
    max_attempts: int = 3,
) -> T:
    """
    Returns a validated instance of `schema`. Retries up to
    `max_attempts` total model calls, feeding back the parse/validation
    error each time, before giving up with LlmJsonFailed.
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    last_error = ""
    for attempt in range(1, max_attempts + 1):
        payload = {
            "model": model,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }
        data = post_json_with_retry(OPENROUTER_URL, json=payload, headers=headers, timeout=60)
        raw_text = data["choices"][0]["message"]["content"]

        try:
            parsed = json_lib.loads(raw_text)
            return schema.model_validate(parsed)
        except (json_lib.JSONDecodeError, ValidationError) as e:
            last_error = str(e)
            print(f"   [schema retry {attempt}/{max_attempts}] invalid output: {last_error[:200]}")
            if attempt < max_attempts:
                # Show the model its own bad output plus the error, so the
                # next attempt can self-correct instead of repeating the
                # same mistake.
                messages.append({"role": "assistant", "content": raw_text})
                messages.append({
                    "role": "user",
                    "content": (
                        "That response was not valid JSON matching the required shape. "
                        f"Error: {last_error}\n"
                        "Return ONLY corrected valid JSON, same shape, no commentary."
                    ),
                })

    raise LlmJsonFailed(f"Model never returned valid JSON matching {schema.__name__}: {last_error}")