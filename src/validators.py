"""Input validation and sanitisation."""
import re

PROFILES = ("healthy", "asthma_respiratory", "heart_condition", "child", "older_adult", "pregnant")
COMMUTES = ("walk", "bicycle", "public_transport", "car", "two_wheeler", "work_from_home")
ACTIVITIES = ("walk", "commute", "run", "cycle", "outdoor_work", "ventilate_home")
_CITY_RE = re.compile(r"^[\w\s\-\.,']{2,60}$", re.UNICODE)


def clean_city(raw: str) -> str:
    """Return a trimmed city name or raise ValueError."""
    city = (raw or "").strip()
    if not _CITY_RE.match(city):
        raise ValueError("Enter a city name (2-60 letters; only - . , ' allowed as symbols).")
    return city


def clean_choice(value: str, allowed: tuple) -> str:
    if value not in allowed:
        raise ValueError(f"Unsupported option: {value!r}")
    return value


def clean_duration(minutes) -> int:
    try:
        m = int(minutes)
    except (TypeError, ValueError):
        raise ValueError("Duration must be a whole number of minutes.") from None
    if not 5 <= m <= 600:
        raise ValueError("Duration must be between 5 and 600 minutes.")
    return m
