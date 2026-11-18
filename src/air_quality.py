"""Open-Meteo client (HTTPS, timeouts, parsed output)."""
from typing import Dict, List

import requests

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
TIMEOUT = 8


class AirQualityError(RuntimeError):
    pass


def geocode(city: str) -> Dict:
    try:
        r = requests.get(GEO_URL, params={"name": city, "count": 1, "language": "en"}, timeout=TIMEOUT)
        r.raise_for_status()
        results = r.json().get("results") or []
    except (requests.RequestException, ValueError) as exc:
        raise AirQualityError("Location service unavailable. Try again shortly.") from exc
    if not results:
        raise AirQualityError(f"City not found: {city}")
    g = results[0]
    return {"name": g["name"], "country": g.get("country", ""), "lat": g["latitude"], "lon": g["longitude"]}


def parse_air_quality(data: Dict) -> Dict:
    try:
        cur = data["current"]
        hourly = data["hourly"]
        return {
            "aqi": cur["us_aqi"], "pm25": cur.get("pm2_5"), "pm10": cur.get("pm10"),
            "times": hourly["time"][:24], "hourly_aqi": hourly["us_aqi"][:24],
        }
    except (KeyError, TypeError) as exc:
        raise AirQualityError("Unexpected air-quality data format.") from exc


def fetch_air_quality(lat: float, lon: float) -> Dict:
    params = {"latitude": lat, "longitude": lon, "current": "us_aqi,pm2_5,pm10",
              "hourly": "us_aqi", "forecast_days": 2, "timezone": "auto"}
    try:
        r = requests.get(AQ_URL, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError) as exc:
        raise AirQualityError("Air-quality service unavailable. Try again shortly.") from exc
    parsed = parse_air_quality(data)
    if parsed["aqi"] is None:
        raise AirQualityError("No AQI data available for this location.")
    return parsed
