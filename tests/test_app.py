import pytest

from src import app, engine


def test_app_validate_valid_inputs():
    raw = {
        "city": "  Bengaluru ",
        "profile": "healthy",
        "activity": "walk",
        "minutes": 30,
        "commute": "public_transport",
        "purifier": True,
    }
    cleaned = app._validate(raw)
    assert cleaned == {
        "city": "Bengaluru",
        "profile": "healthy",
        "activity": "walk",
        "minutes": 30,
        "commute": "public_transport",
        "purifier": True,
    }


def test_app_validate_rejects_invalid_city():
    raw = {
        "city": "12345",
        "profile": "healthy",
        "activity": "walk",
        "minutes": 30,
        "commute": "walk",
        "purifier": False,
    }
    with pytest.raises(ValueError):
        app._validate(raw)


def test_app_plan_context_formatting():
    place = {"name": "Delhi", "country": "India"}
    advice = engine.Advice(
        aqi=155.4,
        category="Unhealthy",
        base_level=3,
        risk_level=3,
        decision="MODIFY",
        mask="Wear N95",
        tips=["Shorten session"],
        best_window=("2026-11-21T06:00", 85.0),
    )
    inputs = {
        "city": "Delhi",
        "profile": "healthy",
        "activity": "walk",
        "minutes": 45,
        "commute": "car",
        "purifier": False,
    }
    ctx = dict(app._plan_context(place, advice, inputs))
    assert ctx["City"] == "Delhi, India"
    assert ctx["US AQI"] == "155"
    assert ctx["Decision (fixed)"] == "MODIFY"
    assert ctx["Cleanest hour"] == "2026-11-21 06:00"
    assert ctx["Has air purifier"] == "no"
