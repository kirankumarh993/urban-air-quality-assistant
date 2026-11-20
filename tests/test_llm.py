from unittest.mock import patch, MagicMock
import requests
from src import llm

CTX = {"City": "Delhi, India", "US AQI": "312"}


def test_prompt_contains_facts_and_sections():
    p = llm.build_prompt(CTX)
    assert "Delhi" in p and "Indoor air hacks" in p and "Never change" in p


def test_no_key_returns_none(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert llm.plan(CTX) is None


def test_success_and_cap(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    resp = MagicMock()
    resp.json.return_value = {"candidates": [{"content": {"parts": [{"text": "x" * 5000}]}}]}
    with patch("src.llm.requests.post", return_value=resp):
        assert len(llm.plan(CTX)) == llm.MAX_CHARS


def test_network_error_returns_none(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    with patch("src.llm.requests.post", side_effect=requests.RequestException):
        assert llm.plan(CTX) is None
