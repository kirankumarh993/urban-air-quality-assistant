from unittest.mock import MagicMock, patch

import pytest
import requests

from src import air_quality

PAYLOAD = {
    "current": {"us_aqi": 80, "pm2_5": 20, "pm10": 30},
    "hourly": {"time": ["t"] * 30, "us_aqi": list(range(30))},
}


def _resp(data):
    resp = MagicMock()
    resp.json.return_value = data
    return resp


def test_geocode_success():
    data = {"results": [{"name": "Delhi", "country": "India", "latitude": 28.6, "longitude": 77.2}]}
    with patch("src.air_quality.requests.get", return_value=_resp(data)):
        assert air_quality.geocode("Delhi") == {"name": "Delhi", "country": "India", "lat": 28.6, "lon": 77.2}


def test_geocode_not_found():
    with patch("src.air_quality.requests.get", return_value=_resp({})):
        with pytest.raises(air_quality.AirQualityError, match="not found"):
            air_quality.geocode("Nowhereville")


def test_geocode_network_error():
    with patch("src.air_quality.requests.get", side_effect=requests.RequestException):
        with pytest.raises(air_quality.AirQualityError, match="unavailable"):
            air_quality.geocode("Delhi")


def test_fetch_limits_to_24_hours():
    with patch("src.air_quality.requests.get", return_value=_resp(PAYLOAD)):
        parsed = air_quality.fetch_air_quality(1.0, 2.0)
    assert parsed["aqi"] == 80
    assert len(parsed["hourly_aqi"]) == air_quality.HOURS_SHOWN


def test_fetch_missing_aqi():
    data = {"current": {"us_aqi": None}, "hourly": {"time": [], "us_aqi": []}}
    with patch("src.air_quality.requests.get", return_value=_resp(data)):
        with pytest.raises(air_quality.AirQualityError, match="No AQI"):
            air_quality.fetch_air_quality(1.0, 2.0)


def test_invalid_json_is_wrapped():
    resp = MagicMock()
    resp.json.side_effect = ValueError
    with patch("src.air_quality.requests.get", return_value=resp):
        with pytest.raises(air_quality.AirQualityError):
            air_quality.fetch_air_quality(1.0, 2.0)


def test_hours_start_from_current_hour():
    times = [f"2026-11-20T{h:02d}:00" for h in range(24)] + [f"2026-11-21T{h:02d}:00" for h in range(24)]
    data = {
        "current": {"us_aqi": 80, "time": "2026-11-20T20:15"},
        "hourly": {"time": times, "us_aqi": list(range(48))},
    }
    parsed = air_quality.parse_air_quality(data)
    assert parsed["times"][0] == "2026-11-20T20:00"
    assert parsed["hourly_aqi"][0] == 20
    assert len(parsed["times"]) == air_quality.HOURS_SHOWN
