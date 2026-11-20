# Urban Air Quality Assistant

**Challenge 6 vertical:** Urban Air Quality Assistant – a personalised assistant that turns live air-quality data into clear, safe, actionable advice for city residents.

## Approach and logic
1. **Context in:** city, health profile (asthma/respiratory, heart condition, child, older adult, pregnant, healthy), planned activity (walk, commute, run, cycle, outdoor work, windows/ventilation) and duration.
2. **Live data:** Open-Meteo Geocoding + Air Quality APIs (free, no API key). Current and 48 h hourly US AQI, PM2.5, PM10.
3. **Transparent rule engine (`src/engine.py`, pure functions):**
   - AQI -> EPA category (Good ... Hazardous).
   - Sensitive groups get a *lower effective threshold* (risk shift), and intense activities add more.
   - Output: risk level, go / modify / avoid decision, mask guidance (N95/FFP2 when needed), ventilation tip, and the **best time window** in the next 24 h found from the hourly forecast.
4. **GenAI personalised plan (`src/llm.py`, Gemini):** given verified facts (city, AQI, profile, activity, daily travel, purifier) it writes four sections: low-emission routine, indoor air hacks, sustainable alternatives, and the direct impact of the user's choices. The rules decide GO/MODIFY/AVOID; the LLM never changes it. Without a key a built-in rule-based plan is shown.

## How it works
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
streamlit run src/app.py
pytest -q
ruff check .   # optional: pip install ruff
```
Optional: copy `.env.example` to `.env` or set `GEMINI_API_KEY` in your environment / Streamlit secrets.

## Project structure
```
src/
  app.py          Streamlit UI (small render/validate helpers)
  engine.py       Pure decision logic: category, risk level, GO/MODIFY/AVOID, fallback plan
  air_quality.py  Open-Meteo client (geocoding + air quality, timeouts, error mapping)
  validators.py   Input whitelisting and sanitising
  llm.py          Gemini wrapper: retries, model fallback, never exposes the key
tests/            pytest suites for engine, validators, API client and Gemini wrapper (network mocked)
ruff.toml         Linter settings (line length 120)
pytest.ini        Test settings
```

## Code quality
- Small single-purpose functions, type hints and docstrings throughout.
- Named constants instead of magic numbers; no duplicated logic.
- Specific exception handling; failures return clear user-facing messages.

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
`pytest` covers category boundaries, risk shifts, decision thresholds, best-window search, validators, the Open-Meteo client and the Gemini wrapper (retry, model fallback, error reasons). All network calls are mocked.

## How GenAI was used (tools, prompt flow, human vs AI)
**Tools and why**
- **Gemini API (default `gemini-3.8-flash`, with automatic fallback to other Flash models):** fast, low-cost, free tier; generates the personalised plan at runtime.
- **Open-Meteo:** free live air-quality data, no key needed.
- **Streamlit Community Cloud:** quick public deployment.
- **AI coding assistant (FordLLM):** scaffolding, debugging and test drafting during development.

**Prompt flow:** UI inputs -> validators (whitelist) -> live AQI -> rule engine (decision, risk, best hour) -> structured prompt (system rules + fact list + four fixed headings, word limit) -> Gemini -> length-capped Markdown -> UI. If the call fails, `engine.lifestyle_plan` supplies the same four sections.

**How prompts evolved:** v1 only rewrote the advice in three friendly sentences. v2 added lifestyle inputs and four fixed sections so output covers routines, indoor hacks, sustainable alternatives and impact. Guardrails were added: fixed decision, no medical claims, context treated as data.

**GenAI handled vs human designed:** GenAI writes the personalised wording and suggestions. Humans designed the risk rules, thresholds, validation, security limits, fallback, tests and UI.
