from unittest.mock import MagicMock, patch

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
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"candidates": [{"content": {"parts": [{"text": "x" * 5000}]}}]}
    with patch("src.llm.requests.post", return_value=resp):
        assert len(llm.plan(CTX)) == llm.MAX_CHARS


def test_network_error_returns_none(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    with patch("src.llm.requests.post", side_effect=requests.RequestException):
        assert llm.plan(CTX) is None


def test_failure_records_reason(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    resp = MagicMock(status_code=400)
    resp.json.return_value = {"error": {"message": "API key not valid"}}
    with patch("src.llm.requests.post", return_value=resp):
        assert llm.plan(CTX) is None
    assert "400" in llm.last_error


def test_retries_transient_error_then_succeeds(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setattr("src.llm.time.sleep", lambda _s: None)
    bad = MagicMock(status_code=503)
    bad.json.return_value = {}
    good = MagicMock(status_code=200)
    good.json.return_value = {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
    with patch("src.llm.requests.post", side_effect=[bad, good]):
        assert llm.plan(CTX) == "ok"
    assert llm.last_error == ""


def test_falls_back_to_next_model_on_404(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    gone = MagicMock(status_code=404)
    gone.json.return_value = {"error": {"message": "no longer available"}}
    good = MagicMock(status_code=200)
    good.json.return_value = {"candidates": [{"content": {"parts": [{"text": "hi"}]}}]}
    with patch("src.llm.requests.post", side_effect=[gone, good]):
        assert llm.plan(CTX) == "hi"


def test_thought_parts_are_ignored(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"candidates": [{"content": {"parts": [
        {"thought": True, "text": "thinking"}, {"text": "answer"}]}}]}
    with patch("src.llm.requests.post", return_value=resp):
        assert llm.plan(CTX) == "answer"
