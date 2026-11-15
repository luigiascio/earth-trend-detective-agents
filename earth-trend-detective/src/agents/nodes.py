"""Nodes of the Earth Trend Detective workflow graph.

LLM nodes decide (what to analyse) and explain; Python nodes compute and check.
"""

from google.adk import Agent, Event

from src.agents.tools import FIRST_YEAR, LAST_YEAR, VARIABLES, ZONES, analyze_trend
from src.contracts import Plan

MODEL = "gemini-3.8-flash"  # verified on location "global", see docs/architettura.md

# Built from tools.py so the prompt and the code share one source of truth.
ZONE_LINES = "\n".join(f"- {name}: {info['environment']}" for name, info in ZONES.items())
VARIABLE_LINES = "\n".join(
    f"- {code}: {info['name']} ({info['unit']})" for code, info in VARIABLES.items()
)

# No curly braces in this text: ADK would read them as state placeholders.
PLANNER_INSTRUCTION = f"""You are the planner of Earth Trend Detective, a system that analyses
climate trends in Campania (southern Italy) with NASA POWER data from {FIRST_YEAR} to {LAST_YEAR}.

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
- "Campania", "the whole region" or no zone named: all zones. "Coast" or "inland":
  choose the zones from their environment.
- Keep the default years unless the user asks for a period. "The last N years" means
  from {LAST_YEAR} - N + 1 to {LAST_YEAR}. Years outside {FIRST_YEAR}-{LAST_YEAR} are not
  available: use the closest valid years and say so in reason.
- Plan every zone the user names, even if two zones look similar.

Out of scope:
- Set out_of_scope to true and leave items empty if the question is not about temperature
  or precipitation trends in Campania: other places, other variables (wind, pollution...),
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


def analyze(plan: dict) -> Event:
    """Run analyze_trend for every item of the plan (no LLM here).

    `plan` is read from state["plan"], written by the planner node.
    Failed analyses do not stop the others: they are collected in `errors`
    so the explanation can say which data were not available.
    """
    if plan.get("out_of_scope") or not plan.get("items"):
        return Event(
            output={"results": 0, "errors": 0},
            state={"results": [], "errors": []},
            route=ROUTE_OUT_OF_SCOPE,
        )

    results, errors = [], []
    seen = set()
    for item in plan["items"]:
        key = (item["zone"], item["variable"], item["start_year"], item["end_year"])
        if key in seen:  # the LLM may repeat an item: compute it only once
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
        state={"results": results, "errors": errors},
        route=ROUTE_OK if results else ROUTE_NO_DATA,
    )
