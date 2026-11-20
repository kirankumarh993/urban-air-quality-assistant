import pytest
from src import engine, validators, air_quality


@pytest.mark.parametrize("aqi,name", [(0, "Good"), (50, "Good"), (51, "Moderate"), (150, "Unhealthy for Sensitive Groups"),
                                     (200, "Unhealthy"), (301, "Hazardous")])
def test_categorize(aqi, name):
    assert engine.categorize(aqi)[0] == name


def test_negative_aqi():
    with pytest.raises(ValueError):
        engine.categorize(-1)


def test_sensitive_higher_risk():
    assert engine.risk_level(120, "asthma_respiratory", "run") > engine.risk_level(120, "healthy", "walk")


def test_good_air_no_shift():
    assert engine.risk_level(30, "asthma_respiratory", "run") == 0


def test_risk_capped():
    assert engine.risk_level(500, "asthma_respiratory", "run", 300) == 5


def test_decisions():
    assert engine.advise(30, "healthy", "walk", 30).decision == "GO"
    assert engine.advise(180, "asthma_respiratory", "run", 60).decision == "AVOID"


def test_mask():
    assert "N95" in engine.advise(250, "healthy", "walk", 30).mask


def test_best_window():
    assert engine.best_window(["a", "b", "c"], [90, 40, None]) == ("b", 40.0)
    assert engine.best_window([], []) is None


def test_ventilate_advice():
    assert "closed" in " ".join(engine.advise(220, "healthy", "ventilate_home", 30).tips)


def test_city_validation():
    assert validators.clean_city("  New Delhi ") == "New Delhi"
    for bad in ["", "<script>", "a", "x" * 61]:
        with pytest.raises(ValueError):
            validators.clean_city(bad)


def test_duration_and_choice():
    assert validators.clean_duration("30") == 30
    for bad in ["abc", 1, 1000]:
        with pytest.raises(ValueError):
            validators.clean_duration(bad)
    with pytest.raises(ValueError):
        validators.clean_choice("x", validators.ACTIVITIES)


def test_parse():
    d = {"current": {"us_aqi": 80, "pm2_5": 20, "pm10": 30}, "hourly": {"time": ["t"], "us_aqi": [80]}}
    assert air_quality.parse_air_quality(d)["aqi"] == 80
    with pytest.raises(air_quality.AirQualityError):
        air_quality.parse_air_quality({})


def test_lifestyle_plan_levels():
    low = engine.lifestyle_plan(0, "car", False)
    high = engine.lifestyle_plan(4, "bicycle", True)
    assert "Normal routine" in low["routine"]
    assert "Stay indoors" in high["routine"]
    assert "HEPA" in " ".join(high["indoor"])
    assert "purifier" in " ".join(low["indoor"]).lower()
    assert "metro" in low["alternative"].lower()


def test_lifestyle_unknown_commute_defaults():
    assert engine.lifestyle_plan(2, "unknown", False)["alternative"]


def test_commute_validation():
    assert validators.clean_choice("car", validators.COMMUTES) == "car"
    with pytest.raises(ValueError):
        validators.clean_choice("rocket", validators.COMMUTES)
