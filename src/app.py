"""Streamlit UI."""
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import air_quality, engine, llm, validators  # noqa: E402

ICON = {0: "🟢", 1: "🟡", 2: "🟠", 3: "🔴", 4: "🟣", 5: "🟤"}
LABELS = {"healthy": "No special condition", "asthma_respiratory": "Asthma / respiratory condition",
          "heart_condition": "Heart condition", "child": "Child", "older_adult": "Older adult (65+)",
          "pregnant": "Pregnant"}
ACT = {"walk": "Walk", "commute": "Commute", "run": "Run / intense exercise", "cycle": "Cycle",
       "outdoor_work": "Outdoor work", "ventilate_home": "Open windows at home"}


@st.cache_data(ttl=900, show_spinner=False)
def load(city: str):
    place = air_quality.geocode(city)
    return place, air_quality.fetch_air_quality(place["lat"], place["lon"])


def main() -> None:
    st.set_page_config(page_title="Urban Air Quality Assistant", page_icon="🌫️")
    st.title("Urban Air Quality Assistant")
    st.caption("Personalised, plain-language air advice. General guidance only, not medical advice.")
    with st.form("ctx"):
        city = st.text_input("City", "Delhi", max_chars=60, help="Type a city name")
        profile = st.selectbox("Health profile", list(LABELS), format_func=LABELS.get)
        activity = st.selectbox("Planned activity", list(ACT), format_func=ACT.get)
        minutes = st.number_input("Duration (minutes)", 5, 600, 45, step=5)
        go = st.form_submit_button("Get advice")
    if not go:
        return
    try:
        city = validators.clean_city(city)
        profile = validators.clean_choice(profile, validators.PROFILES)
        activity = validators.clean_choice(activity, validators.ACTIVITIES)
        minutes = validators.clean_duration(minutes)
        place, data = load(city)
    except (ValueError, air_quality.AirQualityError) as exc:
        st.error(str(exc))
        return
    a = engine.advise(data["aqi"], profile, activity, minutes, data["times"], data["hourly_aqi"])
    st.subheader(f"{place['name']}, {place['country']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("US AQI", round(a.aqi))
    c2.metric("PM2.5 (µg/m³)", data["pm25"])
    c3.metric("PM10 (µg/m³)", data["pm10"])
    st.markdown(f"### {ICON[a.risk_level]} Decision: **{a.decision}** (air: {a.category}, your risk level {a.risk_level}/5)")
    for t in a.tips + [a.mask]:
        st.write("- " + t)
    if a.best_window:
        st.info(f"Cleanest hour in next 24 h: {a.best_window[0].replace('T', ' ')} (AQI about {a.best_window[1]})")
    summary = f"Decision {a.decision}; AQI {round(a.aqi)} ({a.category}); profile {profile}; activity {activity}. " + " ".join(a.tips + [a.mask])
    @st.fragment
    def _explain(summary):
        if st.button("Explain in simple words (AI)"):
           st.write(llm.explain(summary) or "AI explanation unavailable; see the advice above.")

    _explain(summary)


if __name__ == "__main__":
    main()
