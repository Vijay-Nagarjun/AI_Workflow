"""
Shared HTTP helper: POSTs JSON with retry + exponential backoff.

Every outbound call (Tavily search, OpenRouter chat completions) goes
through this instead of a bare `requests.post`, so a single dropped
connection or a 429/5xx from the API doesn't kill the whole batch run.
"""
import random
import time
from typing import Optional

import requests

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class HttpCallFailed(RuntimeError):
    pass


def post_json_with_retry(
    url: str,
    *,
    json: dict,
    headers: Optional[dict] = None,
    timeout: int = 60,
    max_retries: int = 3,
    base_delay: float = 1.5,
) -> dict:
    """
    POST `json` to `url`, retrying on timeouts, connection errors, and
    retryable HTTP status codes (429/500/502/503/504). Backs off
    exponentially with jitter between attempts. Raises HttpCallFailed
    once max_retries is exhausted; any other error (4xx, bad response
    shape) raises immediately via response.raise_for_status().
    """
    last_error: Exception = RuntimeError("no attempt made")

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, json=json, headers=headers, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout) as e:
            last_error = e
        else:
            if response.status_code not in RETRYABLE_STATUS:
                response.raise_for_status()
                return response.json()
            last_error = RuntimeError(
                f"HTTP {response.status_code} from {url}: {response.text[:300]}"
            )

        if attempt < max_retries:
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            print(f"   [retry {attempt}/{max_retries - 1}] {last_error} -- retrying in {delay:.1f}s")
            time.sleep(delay)

    raise HttpCallFailed(f"Gave up after {max_retries} attempts calling {url}: {last_error}")
