"""Input validation and sanitisation."""
import re
from typing import Tuple

PROFILES = ("healthy", "asthma_respiratory", "heart_condition", "child", "older_adult", "pregnant")
COMMUTES = ("walk", "bicycle", "public_transport", "car", "two_wheeler", "work_from_home")
ACTIVITIES = ("walk", "commute", "run", "cycle", "outdoor_work", "ventilate_home")

MIN_MINUTES = 5
MAX_MINUTES = 600
_CITY_RE = re.compile(r"^[\w\s\-\.,']{2,60}$", re.UNICODE)


def clean_city(raw: str) -> str:
    """Return a trimmed city name, or raise ValueError if it is not valid."""
    city = (raw or "").strip()
    if not _CITY_RE.match(city):
        raise ValueError("Enter a city name (2-60 letters; only - . , ' allowed as symbols).")
    return city


def clean_choice(value: str, allowed: Tuple[str, ...]) -> str:
    """Return ``value`` if it is in ``allowed``, otherwise raise ValueError."""
    if value not in allowed:
        raise ValueError(f"Unsupported option: {value!r}")
    return value


def clean_duration(minutes: object) -> int:
    """Return ``minutes`` as an int within the allowed range, or raise ValueError."""
    try:
        value = int(minutes)
    except (TypeError, ValueError):
        raise ValueError("Duration must be a whole number of minutes.") from None
    if not MIN_MINUTES <= value <= MAX_MINUTES:
        raise ValueError(f"Duration must be between {MIN_MINUTES} and {MAX_MINUTES} minutes.")
    return value
