# Urban Air Quality Assistant

**Challenge 6 vertical:** Urban Air Quality Assistant – a personalised assistant that turns live air-quality data into clear, safe, actionable advice for city residents.

## Approach and logic
1. **Context in:** city, health profile (asthma/respiratory, heart condition, child, older adult, pregnant, healthy), planned activity (walk, commute, run, cycle, outdoor work, windows/ventilation) and duration.
2. **Live data:** Open-Meteo Geocoding + Air Quality APIs (free, no API key). Current and 48 h hourly US AQI, PM2.5, PM10.
3. **Transparent rule engine (`src/engine.py`, pure functions):**
   - AQI -> EPA category (Good ... Hazardous).
   - Sensitive groups get a *lower effective threshold* (risk shift), and intense activities add more.
   - Output: risk level, go / modify / avoid decision, mask guidance (N95/FFP2 when needed), ventilation tip, and the **best time window** in the next 24 h found from the hourly forecast.
4. **Optional GenAI (`src/llm.py`):** Gemini rewrites the rule-based result in plain, friendly language. The rules decide; the LLM never changes the decision. Without a key the app falls back to the built-in text.

## How it works
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
streamlit run src/app.py
pytest -q
```
Optional: copy `.env.example` to `.env` or set `GEMINI_API_KEY` in your environment / Streamlit secrets.

## Assumptions
- US AQI scale; Open-Meteo modelled data may differ from local ground stations.
- Advice is general guidance, **not medical advice**. Users with conditions should follow their doctor's plan.
- Risk-shift values are simplified from public EPA/WHO guidance.

## Security
- No secrets in repo; keys come from environment variables.
- Input is validated, length-limited and whitelisted (`validators.py`); API calls use timeouts and HTTPS only.
- Output rendered as text (no unsafe HTML); LLM output is length-capped and never drives decisions.
- Pinned dependency ranges.

## Efficiency
- `st.cache_data` with TTL caches geocoding and air-quality calls; one request per city; LLM called only on user click.

## Accessibility
- Labelled native widgets, keyboard-operable, risk conveyed by text + emoji (not colour alone), plain language, clear error messages.

## Testing
`pytest` covers category boundaries, risk shifts, best-window search, validators and API parsing (mocked network).
