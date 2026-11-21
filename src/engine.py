"""Pure decision logic: AQI + user context -> advice."""
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

# (upper AQI bound, category name, level 0-5)
CATEGORIES = [
    (50, "Good", 0),
    (100, "Moderate", 1),
    (150, "Unhealthy for Sensitive Groups", 2),
    (200, "Unhealthy", 3),
    (300, "Very Unhealthy", 4),
    (float("inf"), "Hazardous", 5),
]
SENSITIVE = {"asthma_respiratory": 2, "heart_condition": 2, "child": 1, "older_adult": 1, "pregnant": 1, "healthy": 0}
INTENSITY = {"ventilate_home": 0, "walk": 0, "commute": 0, "cycle": 1, "outdoor_work": 1, "run": 2}

MAX_LEVEL = 5
LONG_EXPOSURE_MINUTES = 120
GO_MAX_LEVEL = 1
MODIFY_MAX_LEVEL = 3
MASK_OPTIONAL_LEVEL = 2
MEDICATION_TIP_LEVEL = 2
MEDICATION_PROFILES = ("asthma_respiratory", "heart_condition")


@dataclass
class Advice:
    """Result of :func:`advise`."""

    aqi: float
    category: str
    base_level: int
    risk_level: int
    decision: str  # GO / MODIFY / AVOID
    mask: str
    tips: List[str] = field(default_factory=list)
    best_window: Optional[Tuple[str, float]] = None


def categorize(aqi: float) -> Tuple[str, int]:
    """Return ``(category name, level 0-5)`` for a US AQI value."""
    if not math.isfinite(aqi):
        raise ValueError(f"AQI must be a finite number: {aqi!r}")
    if aqi < 0:
        raise ValueError("AQI cannot be negative")
    for upper, name, level in CATEGORIES:
        if aqi <= upper:
            return name, level
    return "Hazardous", MAX_LEVEL


def risk_level(aqi: float, profile: str, activity: str, minutes: int = 30) -> int:
    """Base AQI level plus a shift for sensitivity, intensity and long exposure (capped 0-5)."""
    _, base = categorize(aqi)
    if base == 0:
        return 0  # clean air: no shift
    shift = SENSITIVE.get(profile, 0) + INTENSITY.get(activity, 0)
    long_exposure = 1 if minutes > LONG_EXPOSURE_MINUTES and shift else 0
    shift = (shift + 1) // 2 + long_exposure
    return min(MAX_LEVEL, base + shift)


def decide(level: int) -> str:
    """Map a risk level to GO / MODIFY / AVOID."""
    if level <= GO_MAX_LEVEL:
        return "GO"
    return "MODIFY" if level <= MODIFY_MAX_LEVEL else "AVOID"


def mask_advice(level: int, activity: str) -> str:
    """Return mask guidance for a risk level and activity."""
    if activity == "ventilate_home" or level <= GO_MAX_LEVEL:
        return "No mask needed."
    if level == MASK_OPTIONAL_LEVEL:
        return "A well-fitted mask is optional but helpful in traffic."
    return "Wear a well-fitted N95/FFP2 respirator outdoors."


def best_window(
    times: Sequence[str], aqis: Sequence[Optional[float]], hours: int = 1
) -> Optional[Tuple[str, float]]:
    """Return (start time, avg AQI) of the cleanest window of `hours` consecutive hours."""
    best: Optional[Tuple[str, float]] = None
    for i in range(len(aqis) - hours + 1):
        window = aqis[i:i + hours]
        if any(v is None for v in window):
            continue
        avg = sum(window) / hours
        if best is None or avg < best[1]:
            best = (times[i], round(avg, 1))
    return best


def _activity_tip(activity: str, decision: str) -> str:
    """Return the main tip for the activity and decision."""
    if activity == "ventilate_home":
        if decision == "GO":
            return "Open windows briefly now."
        return "Keep windows closed; use a HEPA purifier if available."
    if decision == "GO":
        return "Air is fine for your plan. Enjoy it."
    if decision == "MODIFY":
        return "Shorten the session, lower the intensity, or pick a park/low-traffic route."
    return "Avoid outdoor exertion now; move the activity indoors or reschedule."


def advise(
    aqi: float,
    profile: str,
    activity: str,
    minutes: int,
    times: Sequence[str] = (),
    hourly: Sequence[Optional[float]] = (),
) -> Advice:
    """Combine AQI and user context into a decision, tips, mask advice and cleanest hour."""
    category, base = categorize(aqi)
    level = risk_level(aqi, profile, activity, minutes)
    decision = decide(level)
    tips = [_activity_tip(activity, decision)]
    if profile in MEDICATION_PROFILES and level >= MEDICATION_TIP_LEVEL:
        tips.append("Carry your prescribed medication and stop if you feel symptoms.")
    window = best_window(times, hourly, 1) if times and hourly else None
    return Advice(aqi, category, base, level, decision, mask_advice(level, activity), tips, window)


COMMUTE_ALT = {
    "car": "Switch some car trips to metro/bus or carpool; fewer cars means less exhaust at street level.",
    "two_wheeler": "Use metro/bus for longer trips, or an electric two-wheeler; wear a fitted N95 in heavy traffic.",
    "bicycle": "Keep cycling (zero emissions) but pick low-traffic lanes and avoid peak rush hour.",
    "walk": "Keep walking (zero emissions); choose park or residential streets away from main roads.",
    "public_transport": (
        "Keep using public transport; it cuts emissions per person. Wait indoors until the vehicle arrives."
    ),
    "work_from_home": "Staying home avoids commute exposure and emissions; combine errands into one trip.",
}
IMPACT_TEXT = (
    "Cutting one car trip avoids tailpipe PM2.5 and CO2 and lowers street-level pollution for your family. "
    "Staying indoors in a closed, clean room can sharply cut the particles you breathe on bad days."
)


def _routine(level: int) -> str:
    """Return the daily-routine line for a risk level."""
    if level <= GO_MAX_LEVEL:
        return "Normal routine is fine. Do outdoor errands and exercise now, and ventilate rooms."
    if level <= MODIFY_MAX_LEVEL:
        return "Shift outdoor tasks to the cleanest hour, keep them short, and avoid busy roads."
    return "Stay indoors where possible, postpone outdoor exercise, and combine errands into one trip."


def _indoor_tips(level: int, has_purifier: bool) -> List[str]:
    """Return three indoor-air tips."""
    windows = "Keep windows closed during peak pollution." if level >= 2 else "Ventilate briefly while air is clean."
    if has_purifier:
        purifier = "Use a HEPA purifier in the room you use most."
    else:
        purifier = "No purifier? Keep windows shut, damp-mop floors, and avoid burning incense or candles."
    return [windows, purifier, "Do not sweep dry or burn waste; both add indoor particles."]


def lifestyle_plan(level: int, commute: str, has_purifier: bool) -> Dict[str, object]:
    """Deterministic fallback plan: routine, indoor hacks, sustainable alternative and impact."""
    return {
        "routine": _routine(level),
        "indoor": _indoor_tips(level, has_purifier),
        "alternative": COMMUTE_ALT.get(commute, COMMUTE_ALT["walk"]),
        "impact": IMPACT_TEXT,
    }
