"""Earth Trend Detective: web interface (Streamlit).

A chat: each answer shows the verdict of the guardrail, the explanation and the charts,
with the computed numbers, the plan and the guardrail checks one click away.
Run from the project root:

    uv run streamlit run app.py
"""

import asyncio
import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / "src" / "agents" / "detective" / ".env")  # Vertex AI settings (not in git)

from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

from src.agents.detective.agent import root_agent  # noqa: E402
from src.agents.nodes import MAX_ATTEMPTS  # noqa: E402
from src.agents.tools import DATA_RAW, ZONES, FIRST_YEAR, LAST_YEAR  # noqa: E402
from src.data.power import fetch_power_monthly, parse_power_monthly  # noqa: E402
from src.guardrail.checks import format_value  # noqa: E402
from src.viz.plots import DARK, TREND_COLORS, plot_trend  # noqa: E402

APP_NAME = "earth_trend_detective"
EXAMPLES = [
    "Is it getting warmer on the coast of Campania?",
    "Are Napoli and Caserta warming at the same rate? And Salerno?",
    "Is it raining less in Avellino over the last 30 years?",
    "What's the weather in Rome tomorrow?",
]


# ---------------------------------------------------------------------------
# Running the graph
# ---------------------------------------------------------------------------

def _describe_step(output) -> str | None:
    """Turn a node output into one line for the progress box (None = not worth showing)."""
    if not isinstance(output, dict):
        return None
    if "out_of_scope" in output:
        if output["out_of_scope"]:
            return "**Planner** (Gemini): question out of scope"
        return f"**Planner** (Gemini): {len(output.get('items', []))} analyses planned"
    if set(output) == {"results", "errors"}:
        return f"**Analysis** (Python): {output['results']} computed, {output['errors']} failed"
    if "claims" in output:
        return "**Explainer** (Gemini): answer written with placeholders"
    if "passed" in output:
        verdict = "passed" if output["passed"] else f"rejected ({len(output['violations'])} problems)"
        return f"**Guardrail** (Python): attempt {output['attempts']} {verdict}"
    return None


async def _run(question: str, status) -> dict:
    runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)
    session = await runner.session_service.create_session(app_name=APP_NAME, user_id="web")
    message = types.Content(role="user", parts=[types.Part(text=question)])

    reports, last = [], time.perf_counter()
    async for event in runner.run_async(user_id="web", session_id=session.id, new_message=message):
        line = _describe_step(event.output)
        if line:
            now = time.perf_counter()
            status.write(f"{line} · {now - last:.1f} s")
            last = now
        if isinstance(event.output, dict) and "passed" in event.output:
            reports.append(event.output)

    session = await runner.session_service.get_session(
        app_name=APP_NAME, user_id="web", session_id=session.id
    )
    return {"question": question, "state": dict(session.state), "reports": reports}


@st.cache_resource
def _event_loop() -> asyncio.AbstractEventLoop:
    """One event loop for the whole app: asyncio.run() would close it while the Gemini
    client still has connections to close ("Event loop is closed" errors)."""
    return asyncio.new_event_loop()


def ask(question: str) -> dict:
    start = time.perf_counter()
    with st.status("Working on it...", expanded=True) as status:
        run = _event_loop().run_until_complete(_run(question, status))
        run["seconds"] = time.perf_counter() - start
        status.update(label=f"Done in {run['seconds']:.0f} s", state="complete", expanded=False)
    return run


# ---------------------------------------------------------------------------
# Charts and tables
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def annual_means(zone: str, variable: str, start: int, end: int) -> pd.Series:
    """Annual mean of the monthly values (from the local cache filled by the analysis)."""
    info = ZONES[zone]
    payload = fetch_power_monthly(
        info["lat"], info["lon"], FIRST_YEAR, LAST_YEAR, DATA_RAW / f"power_monthly_{zone}.json"
    )
    df = parse_power_monthly(payload, zone)
    df = df[(df["variable"] == variable) & df["date"].dt.year.between(start, end)]
    return df.groupby(df["date"].dt.year)["value"].mean()


def show_chart(r: dict) -> None:
    start, end = (int(y) for y in r["period"].split("-"))
    series = annual_means(r["zone"], r["variable"], start, end)
    fig = plot_trend(
        series.index.to_numpy(), series.to_numpy(),
        slope=r["slope_per_decade"] / 10, lower=r["ci_low_per_decade"] / 10,
        upper=r["ci_high_per_decade"] / 10,
        title=f"{r['zone'].capitalize()} · {r['variable_name']} · annual mean",
        unit=format_value("unit", r["unit"]), source=r["source"],
        trend=r["trend"], dark=True,
    )
    st.pyplot(fig)
    plt.close(fig)
    verdict = f"significant {r['trend']} trend" if r["significant"] else "no statistically significant trend"
    st.caption(f"Seasonal Mann-Kendall on monthly data: {verdict}, p-value {format_value('p_value', r['p_value'])}.")


def numbers_table(results: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "zone": r["zone"], "variable": r["variable"], "period": r["period"],
            "trend": r["trend"], "p-value": format_value("p_value", r["p_value"]),
            "slope / decade": format_value("slope_per_decade", r["slope_per_decade"]),
            "95% CI": f"[{r['ci_low_per_decade']:.3f}, {r['ci_high_per_decade']:.3f}]",
            "unit": format_value("unit", r["unit"]),
            "same grid cell as": r["same_grid_cell_as"] or "",
        }
        for r in results
    ])


def render_run(run: dict) -> None:
    """One assistant message: verdict badge, answer, charts, then the details behind it."""
    state, reports = run["state"], run["reports"]
    results, errors = state.get("results") or [], state.get("errors") or []
    plan = state.get("plan") or {}
    report = state.get("guardrail_report")

    if report and report["passed"]:
        st.success(f"Verified by the guardrail at attempt {report['attempts']} of {MAX_ATTEMPTS}.", icon="✅")
    elif report:
        st.warning("No explanation passed the checks: safe summary built from the numbers.", icon="⚠️")
    elif plan.get("out_of_scope"):
        st.info("Out of scope: no analysis was run.", icon="ℹ️")
    # One horizontal row of tabs: the answer is open by default, the details are one click away.
    attempts = len(reports)
    guard_label = f"Guardrail · {attempts} attempt{'' if attempts == 1 else 's'}" if reports else "Guardrail"
    tab_answer, tab_numbers, tab_plan, tab_guard = st.tabs(["Answer", "Numbers", "Plan", guard_label])

    with tab_answer:
        st.markdown((state.get("answer") or "").replace("\n", "  \n"))
        if results:
            chart_cols = st.columns(2)
            for i, r in enumerate(results):
                with chart_cols[i % 2]:
                    show_chart(r)

    with tab_numbers:
        if results:
            st.dataframe(numbers_table(results), hide_index=True, width="stretch")
            st.caption("Computed by src/stats. These are the only numbers that can appear in the answer.")
        for e in errors:
            st.error(f"{e['zone']} · {e['variable']}: {e['message']}")
        if not results and not errors:
            st.write("No analysis was run.")
    with tab_plan:
        st.caption("Chosen by the planner from a closed list of zones and variables.")
        if plan.get("reason"):
            st.markdown(f"**Reason:** {plan['reason']}")
        if plan.get("items"):
            st.dataframe(pd.DataFrame(plan["items"]), hide_index=True, width="stretch")
    with tab_guard:
        if not reports:
            st.write("The guardrail did not run for this question.")
        for rep in reports:
            if rep["passed"]:
                st.success(f"Attempt {rep['attempts']}: all checks passed.")
            else:
                st.error(f"Attempt {rep['attempts']}: rejected")
                for v in rep["violations"]:
                    st.markdown(f"- {v}")
        explanation = state.get("explanation")
        if explanation:
            st.markdown("**Raw explanation from Gemini** (numbers are placeholders, filled in by code):")
            st.code(explanation["text"], language=None, wrap_lines=True)
            st.json({"claims": explanation["claims"], "comparisons": explanation["comparisons"]}, expanded=False)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Earth Trend Detective", page_icon="🌍", layout="wide")

with st.sidebar:
    st.header("How it works")
    st.markdown(
        "1. **Planner** turns your question into analyses: zone, variable, period.\n"
        "2. **Analysis** downloads NASA POWER data and runs a seasonal "
        "Mann-Kendall test with the Sen slope.\n"
        "3. **Explainer** writes the answer with placeholders: it never writes a number.\n"
        f"4. **Guardrail** checks every claim against the numbers. If it fails, the "
        f"explainer retries (up to {MAX_ATTEMPTS} attempts), then a safe template is used."
    )
    legend = " &nbsp; ".join(
        f'<span style="color:{color}">■</span> {label}'
        for label, color in [
            ("observed annual mean", DARK["series"]),
            ("increasing", TREND_COLORS["increasing"]),
            ("decreasing", TREND_COLORS["decreasing"]),
            ("no significant trend", TREND_COLORS["no trend"]),
        ]
    )
    st.markdown(f"Chart colours: {legend}", unsafe_allow_html=True)
    st.header("Data")
    st.markdown(
        f"NASA POWER monthly data (MERRA-2), {FIRST_YEAR}-{LAST_YEAR}: air temperature at 2 m "
        "and precipitation. Five zones in Campania, Italy. Napoli and Caserta, and Avellino and "
        "Benevento, fall in the same grid cell: their data are identical."
    )
    st.caption("Data: NASA Langley Research Center (LaRC) POWER Project, funded through the "
               "NASA Earth Science/Applied Science Program.")
    if st.button("Clear conversation"):
        st.session_state["history"] = []

st.title("Earth Trend Detective")
st.markdown(
    "Ask about **temperature or precipitation trends in Campania**. "
    "The AI plans and explains; the statistics are computed by code, "
    "and every sentence is checked against the numbers before you see it."
)

history = st.session_state.setdefault("history", [])

clicked = None
if not history:
    st.caption("Try one of these:")
    cols = st.columns(len(EXAMPLES))
    for col, example in zip(cols, EXAMPLES):
        if col.button(example, width="stretch"):
            clicked = example

for past in history:
    with st.chat_message("user"):
        st.markdown(past["question"])
    with st.chat_message("assistant"):
        render_run(past)

prompt = st.chat_input("Ask about a trend in Campania (each question is answered on its own)")
question = clicked or (prompt.strip() if prompt else "")
if question:
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        run = ask(question)
        render_run(run)
    history.append(run)
    if clicked:
        st.rerun()  # hide the example buttons once the conversation has started
