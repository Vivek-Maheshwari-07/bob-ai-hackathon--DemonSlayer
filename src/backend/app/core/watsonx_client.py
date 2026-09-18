"""Minimal IBM watsonx.ai REST client.

Uses raw HTTPS calls via httpx (IAM token exchange + the watsonx.ai text
generation endpoint) rather than the ibm-watsonx-ai SDK, consistent with the
existing lightweight Gemini REST integration used elsewhere in this codebase.

Every function fails soft (returns None) so callers can fall back to the
next model in the chain instead of raising.
"""

import time
from typing import Optional

try:
    import httpx
except ImportError:
    httpx = None

from app.core.config import settings

_IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"

_cached_token: Optional[str] = None
_cached_token_expiry: float = 0.0


def is_configured() -> bool:
    """Whether watsonx credentials are present and httpx is available."""
    return bool(httpx is not None and settings.WATSONX_API_KEY and settings.WATSONX_PROJECT_ID)


def _get_iam_token() -> Optional[str]:
    """Exchanges the watsonx API key for a short-lived IBM Cloud IAM bearer token."""
    global _cached_token, _cached_token_expiry

    if httpx is None or not settings.WATSONX_API_KEY:
        return None
    if _cached_token and time.time() < _cached_token_expiry:
        return _cached_token

    try:
        resp = httpx.post(
            _IAM_TOKEN_URL,
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": settings.WATSONX_API_KEY,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("access_token")
            expires_in = data.get("expires_in", 3000)
            if token:
                _cached_token = token
                _cached_token_expiry = time.time() + max(int(expires_in) - 60, 60)
                return token
    except Exception:
        pass
    return None


def generate_text(
    prompt: str,
    max_new_tokens: int = 600,
    temperature: float = 0.1,
) -> Optional[str]:
    """Calls the IBM watsonx.ai foundation model text generation endpoint.

    Returns the generated text, or None if watsonx is not configured or the
    call fails for any reason (network, auth, malformed response, etc).
    """
    if not is_configured():
        return None

    token = _get_iam_token()
    if not token:
        return None

    url = f"{settings.WATSONX_URL.rstrip('/')}/ml/v1/text/generation?version=2024-05-01"
    payload = {
        "model_id": settings.WATSONX_MODEL_ID,
        "project_id": settings.WATSONX_PROJECT_ID,
        "input": prompt,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "repetition_penalty": 1.05,
        },
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=20.0)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if results:
                text = results[0].get("generated_text", "")
                if text and text.strip():
                    return text.strip()
    except Exception:
        pass
    return None
