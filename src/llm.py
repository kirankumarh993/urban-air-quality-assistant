"""Optional Gemini wrapper. Falls back silently to rule-based text."""
import os
from typing import Optional

import requests

MAX_CHARS = 600


def explain(summary: str) -> Optional[str]:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    prompt = ("Rewrite this air-quality advice in 3 friendly plain-language sentences. "
              "Do not change the decision or add medical claims.\n" + summary[:1000])
    try:
        r = requests.post(url, headers={"x-goog-api-key": key}, timeout=15,
                          json={"contents": [{"parts": [{"text": prompt}]}]})
        r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return text.strip()[:MAX_CHARS]
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return None
