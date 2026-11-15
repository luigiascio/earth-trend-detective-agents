"""Nodes of the Earth Trend Detective workflow graph.

LLM nodes decide (what to analyse) and explain; Python nodes compute and check.
"""

from google.adk import Agent, Event

from src.agents.tools import FIRST_YEAR, LAST_YEAR, VARIABLES, ZONES, analyze_trend, zone_label
from src.contracts import Explanation, GuardrailReport, Plan
from src.guardrail.checks import PLACEHOLDER_FIELDS, check_explanation, fill_placeholders, format_value

MODEL = "gemini-3.8-flash"  # verified on location "global", see docs/architettura.md

# Built from tools.py so the prompt and the code share one source of truth.
ZONE_LINES = "\n".join(f"- {name}: {info['region']}; {info['environment']}" for name, info in ZONES.items())
VARIABLE_LINES = "\n".join(
    f"- {code}: {info['name']} ({info['unit']})" for code, info in VARIABLES.items()
)

# No curly braces in this text: ADK would read them as state placeholders.
PLANNER_INSTRUCTION = f"""You are the planner of Earth Trend Detective, a system that analyses
climate trends in Italy with NASA POWER data from {FIRST_YEAR} to {LAST_YEAR}, in the 20
regional capitals.

Your only job is to decide which analyses answer the user's question. You never compute,
estimate or report numbers: other parts of the system do that.

Available zones:
{ZONE_LINES}

Available variables:
{VARIABLE_LINES}

How to plan:
- Add one item for each (zone, variable) pair the question needs.
- Warming, heat, cold, temperature: T2M. Rain, drought, precipitation: PRECTOTCORR.
  A general question about the climate: both variables.
- "Italy", "the whole country" or no zone named: all zones. Areas such as "the north",
  "the south", "the islands", "the Alps", "the coast", "the mountains" or "the Adriatic":
  choose the zones from their environment.
- A region (e.g. Sicily, Tuscany): use its capital (palermo, firenze). A town that is not a
  zone (e.g. Verona, Catania): use the capital of its region and say so in reason.
- Keep the default years unless the user asks for a period. "The last N years" means
  from {LAST_YEAR} - N + 1 to {LAST_YEAR}. Years outside {FIRST_YEAR}-{LAST_YEAR} are not
  available: use the closest valid years and say so in reason.
- Plan every zone the user names, even if two zones look similar.

Out of scope:
- Set out_of_scope to true and leave items empty if the question is not about temperature
  or precipitation trends in Italy: places outside Italy, other variables (wind, pollution...),
  weather forecasts, or other topics.
- Always write one short sentence in reason explaining your decision.
"""

planner = Agent(
    name="planner",
    model=MODEL,
    description="Turns the user's question into a plan of trend analyses.",
    instruction=PLANNER_INSTRUCTION,
    output_schema=Plan,
    output_key="plan",
)


# Routes chosen by the analysis node (the graph maps each one to the next node).
ROUTE_OK = "OK"
ROUTE_OUT_OF_SCOPE = "OUT_OF_SCOPE"
ROUTE_NO_DATA = "NO_DATA"

# Every (zone, variable) pair once: the cap that the plan schema cannot express (see contracts.py).
MAX_ANALYSES = len(ZONES) * len(VARIABLES)

# The session state survives across questions: clear what belongs to the previous one.
_RESET = {"guardrail_attempts": 0, "guardrail_feedback": [], "guardrail_report": None, "answer": None}


def analyze(plan: dict) -> Event:
    """Run analyze_trend for every item of the plan (no LLM here).

    `plan` is read from state["plan"], written by the planner node.
    Failed analyses do not stop the others: they are collected in `errors`
    so the explanation can say which data were not available.
    """
    if plan.get("out_of_scope") or not plan.get("items"):
        return Event(
            output={"results": 0, "errors": 0},
            state={"results": [], "errors": [], **_RESET},
            route=ROUTE_OUT_OF_SCOPE,
        )

    results, errors = [], []
    seen = set()
    for item in plan["items"]:
        key = (item["zone"], item["variable"], item["start_year"], item["end_year"])
        if key in seen:  # the LLM may repeat an item: compute it only once
            continue
        if len(seen) >= MAX_ANALYSES:
            errors.append({**item, "message": f"Not computed: at most {MAX_ANALYSES} analyses per question."})
            continue
        seen.add(key)

        result = analyze_trend(**item)
        if result["status"] == "success":
            results.append(result)
        else:
            # Keep what was asked, so the explanation can name the missing analysis.
            errors.append({**item, "message": result["message"]})

    return Event(
        output={"results": len(results), "errors": len(errors)},
        state={"results": results, "errors": errors, **_RESET},
        route=ROUTE_OK if results else ROUTE_NO_DATA,
    )


EXPLAINER_RULES = """You are the explainer of Earth Trend Detective. You turn statistical results
about climate trends in Italy into a short, clear answer for the user.

Writing numbers:
- Your text must contain NO digits at all. Write every number, period, unit, source and
  method as a placeholder [zone.variable.field], for example [napoli.T2M.slope_per_decade].
  Code replaces each placeholder with the exact value, so never copy the values yourself.
- Allowed fields: """ + ", ".join(PLACEHOLDER_FIELDS) + """.
- Use only zones and variables listed in the results below.
- A slope is per decade: write e.g. "[napoli.T2M.slope_per_decade] [napoli.T2M.unit] per decade".

Interpreting results (rules from docs/statistica.md):
- Significance is decided on the q-value: the p-value corrected (Benjamini-Hochberg) for
  testing all n_tests zones with the same variable and period. Cite the q-value, not only
  the p-value, and say once that the result is corrected for multiple tests.
- significant = False: say "no statistically significant trend". Never say "stable",
  "unchanged" or "not changing".
- significant = True: state the direction and the slope with its confidence interval.
- A significant trend is not necessarily large; a p-value is not the probability that the
  trend is real.
- Say that one zone changes faster than another only if their confidence intervals do not
  overlap; otherwise say the difference cannot be established.
- If two zones share the same grid cell (same_grid_cell_as), say their data are identical
  and cannot be compared.
- If some analyses failed, say which data were not available.
- If the user asked about a place that is not a zone, say which zone was used for it.
- With many results, group zones with similar results instead of repeating every number.
- End with the source and the method, as placeholders.
- Answer in the language of the user's question.

Structured fields:
- claims: one entry for every result you mention, with the direction you state
  ("no trend" when you say there is no statistically significant trend).
- comparisons: one entry for every comparison between two zones you make.
"""


def _describe_result(r: dict) -> str:
    return (
        f"- {r['zone']}.{r['variable']} ({r['variable_name']}, {r['region']}, {r['environment']}): "
        f"trend={r['trend']}, significant={r['significant']}, p_value={r['p_value']}, "
        f"q_value={r['q_value']} (n_tests={r['n_tests']}), "
        f"slope_per_decade={r['slope_per_decade']}, confidence interval per decade="
        f"[{r['ci_low_per_decade']}, {r['ci_high_per_decade']}] {r['unit']}, "
        f"period={r['period']}, same_grid_cell_as={r['same_grid_cell_as']}"
    )


def explainer_instruction(ctx) -> str:
    """Build the explainer prompt from the session state (results, errors, guardrail feedback).

    A callable instruction is not templated by ADK, so braces in the data are safe.
    """
    results = ctx.state.get("results", [])
    errors = ctx.state.get("errors", [])
    question = ctx.user_content.parts[0].text if ctx.user_content and ctx.user_content.parts else ""
    parts = [EXPLAINER_RULES, f"User question: {question}", "Results:", *(_describe_result(r) for r in results)]
    if errors:
        parts.append("Analyses that failed:")
        parts += [f"- {e['zone']}.{e['variable']}: {e['message']}" for e in errors]
    feedback = ctx.state.get("guardrail_feedback")
    if feedback:
        parts.append("Your previous answer was rejected by the checker. Fix these problems:")
        parts += [f"- {problem}" for problem in feedback]
    return "\n".join(parts)


explainer = Agent(
    name="explainer",
    model=MODEL,
    description="Explains the computed trends in words, with placeholders instead of numbers.",
    instruction=explainer_instruction,
    output_schema=Explanation,
    output_key="explanation",
)


# ---------------------------------------------------------------------------
# Guardrail and final answers (Python only)
# ---------------------------------------------------------------------------

MAX_ATTEMPTS = 3  # first explanation + 2 retries
ROUTE_PASS = "PASS"
ROUTE_RETRY = "RETRY"
ROUTE_FALLBACK = "FALLBACK"


def guardrail(explanation: dict, results: list, ctx) -> Event:
    """Check the explanation against the results; choose PASS, RETRY or FALLBACK."""
    attempts = ctx.state.get("guardrail_attempts", 0) + 1
    violations = check_explanation(explanation, results)
    report = GuardrailReport(passed=not violations, violations=violations, attempts=attempts).model_dump()
    state = {"guardrail_attempts": attempts, "guardrail_report": report}

    if not violations:
        state["answer"] = fill_placeholders(explanation["text"], results)
        return Event(output=report, state=state, route=ROUTE_PASS)
    if attempts < MAX_ATTEMPTS:
        state["guardrail_feedback"] = violations  # read by explainer_instruction
        return Event(output=report, state=state, route=ROUTE_RETRY)
    return Event(output=report, state=state, route=ROUTE_FALLBACK)


def respond(answer: str) -> Event:
    """Show the checked answer (placeholders already replaced by the guardrail)."""
    return Event(output=answer, message=answer)


def _safe_sentence(r: dict) -> str:
    slope = format_value("slope_per_decade", r["slope_per_decade"])
    low = format_value("ci_low_per_decade", r["ci_low_per_decade"])
    high = format_value("ci_high_per_decade", r["ci_high_per_decade"])
    unit = format_value("unit", r["unit"])
    q = format_value("q_value", r["q_value"])
    numbers = f"{slope} {unit} per decade, 95% CI {low} to {high}, q-value {q}"
    if r["significant"]:
        verdict = f"statistically significant {r['trend']} trend ({numbers})"
    else:
        verdict = f"no statistically significant trend ({numbers})"
    sentence = f"- {zone_label(r['zone'])}, {r['variable_name']}, {r['period']}: {verdict}."
    if r["same_grid_cell_as"]:
        sentence += f" Same NASA POWER grid cell as {zone_label(r['same_grid_cell_as'])}: identical data."
    return sentence


def safe_answer(results: list, errors: list) -> Event:
    """Fallback: a fixed template filled with the true numbers, used when no explanation passes."""
    lines = ["Automatic summary of the computed results:"]
    lines += [_safe_sentence(r) for r in results]
    lines += [f"- {zone_label(e['zone'])}, {e['variable']}: data not available ({e['message']})." for e in errors]
    if results:
        lines.append(f"Source: {results[0]['source']}. Method: {results[0]['method']}, significance level {results[0]['alpha']}.")
    text = "\n".join(lines)
    return Event(output=text, state={"answer": text}, message=text)


OUT_OF_SCOPE_MESSAGE = (
    "I can only answer questions about temperature and precipitation trends in Italy, "
    f"in these zones: {', '.join(zone_label(z) for z in ZONES)}, "
    f"using NASA POWER data from {FIRST_YEAR} to {LAST_YEAR}."
)


def out_of_scope() -> Event:
    return Event(output=OUT_OF_SCOPE_MESSAGE, state={"answer": OUT_OF_SCOPE_MESSAGE}, message=OUT_OF_SCOPE_MESSAGE)


def no_data(errors: list) -> Event:
    lines = ["None of the requested analyses could be computed:"]
    lines += [f"- {zone_label(e['zone'])}, {e['variable']}: {e['message']}" for e in errors]
    text = "\n".join(lines)
    return Event(output=text, state={"answer": text}, message=text)
