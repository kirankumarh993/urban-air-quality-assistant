"""Pure decision logic: AQI + user context -> advice."""
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

CATEGORIES = [  # (upper bound, name, level 0-5)
    (50, "Good", 0),
    (100, "Moderate", 1),
    (150, "Unhealthy for Sensitive Groups", 2),
    (200, "Unhealthy", 3),
    (300, "Very Unhealthy", 4),
    (10**6, "Hazardous", 5),
]
SENSITIVE = {"asthma_respiratory": 2, "heart_condition": 2, "child": 1, "older_adult": 1, "pregnant": 1, "healthy": 0}
INTENSITY = {"ventilate_home": 0, "walk": 0, "commute": 0, "cycle": 1, "outdoor_work": 1, "run": 2}


@dataclass
class Advice:
    aqi: float
    category: str
    base_level: int
    risk_level: int
    decision: str  # GO / MODIFY / AVOID
    mask: str
    tips: List[str] = field(default_factory=list)
    best_window: Optional[Tuple[str, float]] = None


def categorize(aqi: float) -> Tuple[str, int]:
    if aqi < 0:
        raise ValueError("AQI cannot be negative")
    for upper, name, level in CATEGORIES:
        if aqi <= upper:
            return name, level
    raise AssertionError("unreachable")


def risk_level(aqi: float, profile: str, activity: str, minutes: int = 30) -> int:
    """Base AQI level plus a shift for sensitivity, intensity and long exposure (capped 0-5)."""
    _, base = categorize(aqi)
    if base == 0:
        return 0  # clean air: no shift
    shift = SENSITIVE.get(profile, 0) + INTENSITY.get(activity, 0)
    shift = (shift + 1) // 2 + (1 if minutes > 120 and shift else 0)
    return min(5, base + shift)


def mask_advice(level: int, activity: str) -> str:
    if activity == "ventilate_home" or level <= 1:
        return "No mask needed."
    if level == 2:
        return "A well-fitted mask is optional but helpful in traffic."
    return "Wear a well-fitted N95/FFP2 respirator outdoors."


def best_window(times: Sequence[str], aqis: Sequence[Optional[float]], hours: int = 1) -> Optional[Tuple[str, float]]:
    """Return (start time, avg AQI) of the cleanest window of `hours` consecutive hours."""
    best = None
    for i in range(len(aqis) - hours + 1):
        win = aqis[i:i + hours]
        if any(v is None for v in win):
            continue
        avg = sum(win) / hours
        if best is None or avg < best[1]:
            best = (times[i], round(avg, 1))
    return best


def advise(aqi: float, profile: str, activity: str, minutes: int,
           times: Sequence[str] = (), hourly: Sequence[Optional[float]] = ()) -> Advice:
    cat, base = categorize(aqi)
    lvl = risk_level(aqi, profile, activity, minutes)
    if activity == "ventilate_home":
        decision = "GO" if lvl <= 1 else ("MODIFY" if lvl <= 3 else "AVOID")
    else:
        decision = "GO" if lvl <= 1 else ("MODIFY" if lvl <= 3 else "AVOID")
    tips: List[str] = []
    if activity == "ventilate_home":
        tips.append("Open windows briefly now." if decision == "GO" else "Keep windows closed; use a HEPA purifier if available.")
    elif decision == "GO":
        tips.append("Air is fine for your plan. Enjoy it.")
    elif decision == "MODIFY":
        tips.append("Shorten the session, lower the intensity, or pick a park/low-traffic route.")
    else:
        tips.append("Avoid outdoor exertion now; move the activity indoors or reschedule.")
    if profile in ("asthma_respiratory", "heart_condition") and lvl >= 2:
        tips.append("Carry your prescribed medication and stop if you feel symptoms.")
    window = best_window(times, hourly, 1) if times and hourly else None
    return Advice(aqi, cat, base, lvl, decision, mask_advice(lvl, activity), tips, window)


COMMUTE_ALT = {
    "car": "Switch some car trips to metro/bus or carpool; fewer cars means less exhaust at street level.",
    "two_wheeler": "Use metro/bus for longer trips, or an electric two-wheeler; wear a fitted N95 in heavy traffic.",
    "bicycle": "Keep cycling (zero emissions) but pick low-traffic lanes and avoid peak rush hour.",
    "walk": "Keep walking (zero emissions); choose park or residential streets away from main roads.",
    "public_transport": "Keep using public transport; it cuts emissions per person. Wait indoors until the vehicle arrives.",
    "work_from_home": "Staying home avoids commute exposure and emissions; combine errands into one trip.",
}


def lifestyle_plan(level: int, commute: str, has_purifier: bool) -> dict:
    """Deterministic fallback plan: routine, indoor hacks, sustainable alternative and impact."""
    if level <= 1:
        routine = "Normal routine is fine. Do outdoor errands and exercise now, and ventilate rooms."
    elif level <= 3:
        routine = "Shift outdoor tasks to the cleanest hour, keep them short, and avoid busy roads."
    else:
        routine = "Stay indoors where possible, postpone outdoor exercise, and combine errands into one trip."
    indoor = ["Keep windows closed during peak pollution." if level >= 2 else "Ventilate briefly while air is clean.",
              "Use a HEPA purifier in the room you use most." if has_purifier
              else "No purifier? Keep windows shut, damp-mop floors, and avoid burning incense or candles.",
              "Do not sweep dry or burn waste; both add indoor particles."]
    impact = ("Cutting one car trip avoids tailpipe PM2.5 and CO2 and lowers street-level pollution for your family. "
              "Staying indoors in a closed, clean room can sharply cut the particles you breathe on bad days.")
    return {"routine": routine, "indoor": indoor, "alternative": COMMUTE_ALT.get(commute, COMMUTE_ALT["walk"]), "impact": impact}
