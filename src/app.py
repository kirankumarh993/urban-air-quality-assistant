"""Streamlit UI."""
import os
from typing import Dict, Optional, Tuple

import streamlit as st

try:
    from src import air_quality, engine, llm, validators
except ImportError:
    import air_quality  # type: ignore[no-redef]
    import engine  # type: ignore[no-redef]
    import llm  # type: ignore[no-redef]
    import validators  # type: ignore[no-redef]

RISK_BADGE = {
    0: "🟢 Low Risk",
    1: "🟡 Moderate Risk",
    2: "🟠 Elevated Risk",
    3: "🔴 High Risk",
    4: "🟣 Very High Risk",
    5: "🟤 Hazardous Risk",
}
LABELS = {
    "healthy": "No special condition",
    "asthma_respiratory": "Asthma / respiratory condition",
    "heart_condition": "Heart condition",
    "child": "Child",
    "older_adult": "Older adult (65+)",
    "pregnant": "Pregnant",
}
COMMUTE = {
    "walk": "Walk",
    "bicycle": "Bicycle",
    "public_transport": "Bus / metro / train",
    "car": "Car",
    "two_wheeler": "Motorbike / scooter",
    "work_from_home": "Work from home",
}
ACT = {
    "walk": "Walk",
    "commute": "Commute",
    "run": "Run / intense exercise",
    "cycle": "Cycle",
    "outdoor_work": "Outdoor work",
    "ventilate_home": "Open windows at home",
}
CACHE_TTL_S = 900
DEFAULT_CITY = "Delhi"
DEFAULT_MINUTES, MINUTES_STEP = 45, 5
API_KEY_NAME = "GEMINI_API_KEY"


@st.cache_data(ttl=CACHE_TTL_S, show_spinner=False)
def ai_plan(ctx_items: tuple) -> str:
    """Return the Gemini plan; raise RuntimeError on failure (so failures are not cached)."""
    result = llm.plan(dict(ctx_items))
    if not result.text:
        raise RuntimeError(result.error or "unknown error")
    return result.text


@st.cache_data(ttl=CACHE_TTL_S, show_spinner=False)
def load(city: str) -> Tuple[Dict, Dict]:
    """Geocode ``city`` and fetch its air quality (cached for 15 minutes)."""
    place = air_quality.geocode(city)
    return place, air_quality.fetch_air_quality(place["lat"], place["lon"])


def _ensure_api_key() -> None:
    """Copy the Gemini key from Streamlit secrets into the environment if it is not set."""
    if os.environ.get(API_KEY_NAME):
        return
    try:
        os.environ[API_KEY_NAME] = str(st.secrets[API_KEY_NAME])
    except (KeyError, FileNotFoundError):
        pass  # no secrets configured: the rule-based plan is used


def _read_form() -> Optional[Dict[str, object]]:
    """Render the input form; return the raw values once submitted, else None."""
    with st.form("ctx"):
        city = st.text_input(
            "City",
            DEFAULT_CITY,
            max_chars=validators.MAX_CITY_CHARS,
            help="Enter a city name (2 to 60 letters).",
        )
        profile = st.selectbox(
            "Health profile",
            list(LABELS),
            format_func=LABELS.get,
            help="Select any respiratory, cardiac, or age-related sensitivity.",
        )
        activity = st.selectbox(
            "Planned activity",
            list(ACT),
            format_func=ACT.get,
            help="Choose the outdoor activity or home ventilation you plan to do.",
        )
        minutes = st.number_input(
            "Duration (minutes)",
            validators.MIN_MINUTES,
            validators.MAX_MINUTES,
            DEFAULT_MINUTES,
            step=MINUTES_STEP,
            help="How long the planned activity or exposure will last (5 to 600 minutes).",
        )
        commute = st.selectbox(
            "Usual daily travel",
            list(COMMUTE),
            format_func=COMMUTE.get,
            help="Your primary mode of daily travel for tailored low-emission tips.",
        )
        purifier = st.checkbox(
            "I have an air purifier at home",
            help="Check this if you have a HEPA or indoor air purifier available.",
        )
        submitted = st.form_submit_button("Get advice")
    if not submitted:
        return None
    return {
        "city": city,
        "profile": profile,
        "activity": activity,
        "minutes": minutes,
        "commute": commute,
        "purifier": bool(purifier),
    }


def _validate(raw: Dict[str, object]) -> Dict[str, object]:
    """Validate form values; raise ValueError on bad input."""
    return {
        "city": validators.clean_city(str(raw["city"])),
        "profile": validators.clean_choice(str(raw["profile"]), validators.PROFILES),
        "activity": validators.clean_choice(str(raw["activity"]), validators.ACTIVITIES),
        "minutes": validators.clean_duration(raw["minutes"]),
        "commute": validators.clean_choice(str(raw["commute"]), validators.COMMUTES),
        "purifier": bool(raw["purifier"]),
    }


def _window_text(advice: engine.Advice) -> str:
    """Return the cleanest-hour start time as readable text."""
    return advice.best_window[0].replace("T", " ") if advice.best_window else "unknown"


def _render_advice(place: Dict, data: Dict, advice: engine.Advice) -> None:
    """Show the metrics, decision, tips and cleanest hour."""
    st.subheader(f"{place['name']}, {place['country']}")
    col1, col2, col3 = st.columns(3)
    col1.metric("US AQI", round(advice.aqi), help="US Air Quality Index (0-50 Good, 101+ Unhealthy for Sensitive Groups).")
    col2.metric("PM2.5 (µg/m³)", data["pm25"], help="Fine inhalable particles 2.5 micrometers or smaller.")
    col3.metric("PM10 (µg/m³)", data["pm10"], help="Inhalable particles 10 micrometers or smaller.")
    st.markdown(
        f"### Decision: **{advice.decision}** — {RISK_BADGE[advice.risk_level]} "
        f"(Air: {advice.category}, level {advice.risk_level}/5)"
    )
    for tip in advice.tips + [advice.mask]:
        st.write("- " + tip)
    if advice.best_window:
        st.info(f"Cleanest hour in next 24 h: {_window_text(advice)} (AQI about {advice.best_window[1]})")


def _plan_context(place: Dict, advice: engine.Advice, inputs: Dict[str, object]) -> tuple:
    """Build the (hashable) facts passed to Gemini."""
    return (
        ("City", f"{place['name']}, {place['country']}"),
        ("US AQI", str(round(advice.aqi))),
        ("Category", advice.category),
        ("Decision (fixed)", advice.decision),
        ("Health profile", LABELS[str(inputs["profile"])]),
        ("Planned activity", ACT[str(inputs["activity"])]),
        ("Usual travel", COMMUTE[str(inputs["commute"])]),
        ("Has air purifier", "yes" if inputs["purifier"] else "no"),
        ("Cleanest hour", _window_text(advice)),
    )


def _render_fallback(base: Dict[str, object], err: str) -> None:
    """Show the built-in rule-based plan."""
    st.caption("AI plan unavailable, showing the built-in rule-based plan.")
    if err:
        st.caption(f"Reason: {err}")
    st.markdown(f"**1. Low-emission routine for today**\n\n- {base['routine']}")
    st.markdown("**2. Indoor air hacks**\n\n" + "\n".join("- " + t for t in base["indoor"]))
    st.markdown(f"**3. Sustainable alternatives**\n\n- {base['alternative']}")
    st.markdown(f"**4. Impact of your choices**\n\n{base['impact']}")


def _render_plan(ctx: tuple, base: Dict[str, object]) -> None:
    """Show the Gemini plan, or the rule-based fallback if it fails."""
    st.subheader("Your personalised low-emission plan")
    _ensure_api_key()
    err = ""
    text: Optional[str] = None
    with st.spinner("Preparing your plan..."):
        try:
            text = ai_plan(ctx)
        except RuntimeError as exc:
            err = str(exc)
    if text:
        st.caption("Generated by Gemini from the facts above. The decision itself comes from transparent rules.")
        st.markdown(text)
    else:
        _render_fallback(base, err)


def _render_results(raw: Dict[str, object]) -> None:
    """Validate the form values, load live data and render advice plus plan."""
    try:
        inputs = _validate(raw)
        place, data = load(str(inputs["city"]))
    except (ValueError, air_quality.AirQualityError) as exc:
        st.error(str(exc))
        return
    advice = engine.advise(
        data["aqi"],
        str(inputs["profile"]),
        str(inputs["activity"]),
        int(inputs["minutes"]),
        data["times"],
        data["hourly_aqi"],
    )
    _render_advice(place, data, advice)
    base = engine.lifestyle_plan(advice.risk_level, str(inputs["commute"]), bool(inputs["purifier"]))
    st.divider()
    _render_plan(_plan_context(place, advice, inputs), base)


def main() -> None:
    """Run the Streamlit app: inputs on the left, results on the right."""
    st.set_page_config(page_title="Urban Air Quality Assistant", page_icon="🌫️", layout="wide")
    st.title("Urban Air Quality Assistant")
    st.caption("Personalised, plain-language air advice. General guidance only, not medical advice.")
    left, right = st.columns([1, 2], gap="large")
    with left:
        raw = _read_form()
    with right:
        if raw is None:
            st.info("Fill in your details on the left and press **Get advice** to see your air quality and plan here.")
        else:
            _render_results(raw)


if __name__ == "__main__":
    main()