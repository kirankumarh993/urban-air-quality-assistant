"""Open-Meteo client (HTTPS, timeouts, parsed output)."""
from typing import Dict, List, Optional, Tuple

import requests

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
TIMEOUT = 8
HOURS_SHOWN = 24


class AirQualityError(RuntimeError):
    """Raised for any user-facing problem getting location or air-quality data."""


def _get_json(url: str, params: Dict, error_message: str) -> Dict:
    """GET ``url`` and return decoded JSON, mapping network/format errors to AirQualityError."""
    try:
        response = requests.get(url, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        raise AirQualityError(error_message) from exc


def geocode(city: str) -> Dict:
    """Return ``{name, country, lat, lon}`` for the best match of ``city``."""
    data = _get_json(
        GEO_URL,
        {"name": city, "count": 1, "language": "en"},
        "Location service unavailable. Try again shortly.",
    )
    results = data.get("results") or []
    if not results:
        raise AirQualityError(f"City not found: {city}")
    match = results[0]
    return {
        "name": match["name"],
        "country": match.get("country", ""),
        "lat": match["latitude"],
        "lon": match["longitude"],
    }


def _upcoming(times: List[str], values: List, current_time: Optional[str]) -> Tuple[List[str], List]:
    """Return the hourly entries from the current hour onwards (all of them if the time is unknown)."""
    if not current_time:
        return times, values
    cutoff = current_time[:13] + ":00"  # ISO strings compare correctly; drop minutes
    start = next((i for i, t in enumerate(times) if t >= cutoff), len(times))
    return times[start:], values[start:]


def parse_air_quality(data: Dict) -> Dict:
    """Extract current AQI/PM values and the next 24 hourly AQIs (starting from the current hour)."""
    try:
        current = data["current"]
        hourly = data["hourly"]
        times, aqis = _upcoming(hourly["time"], hourly["us_aqi"], current.get("time"))
        return {
            "aqi": current["us_aqi"],
            "pm25": current.get("pm2_5"),
            "pm10": current.get("pm10"),
            "times": times[:HOURS_SHOWN],
            "hourly_aqi": aqis[:HOURS_SHOWN],
        }
    except (KeyError, TypeError, AttributeError) as exc:
        raise AirQualityError("Unexpected air-quality data format.") from exc


def fetch_air_quality(lat: float, lon: float) -> Dict:
    """Fetch and parse air quality for a coordinate; raise AirQualityError if unavailable."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "us_aqi,pm2_5,pm10",
        "hourly": "us_aqi",
        "forecast_days": 2,
        "timezone": "auto",
    }
    data = _get_json(AQ_URL, params, "Air-quality service unavailable. Try again shortly.")
    parsed = parse_air_quality(data)
    if parsed["aqi"] is None:
        raise AirQualityError("No AQI data available for this location.")
    return parsed
