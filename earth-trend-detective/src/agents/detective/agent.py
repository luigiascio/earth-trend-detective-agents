"""Earth Trend Detective as a workflow graph (ADK 2.x).

    planner (LLM) -> analyze (Python) -> explainer (LLM) -> guardrail (Python) -> respond
                         |                    ^                  |
                         |                    +------ RETRY -----+
                         +-> out_of_scope / no_data              +-> FALLBACK -> safe_answer

Run from the project root:
    uv run adk web src/agents      (browser UI, choose "detective")
    uv run adk run src/agents/detective
"""

import sys
from pathlib import Path

# ADK loads this folder as a top-level package: make the project root importable for `src.*`.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from google.adk import Workflow  # noqa: E402

from src.agents.nodes import (  # noqa: E402
    ROUTE_FALLBACK, ROUTE_NO_DATA, ROUTE_OK, ROUTE_OUT_OF_SCOPE, ROUTE_PASS, ROUTE_RETRY,
    analyze, explainer, guardrail, no_data, out_of_scope, planner, respond, safe_answer,
)

root_agent = Workflow(
    name="earth_trend_detective_graph",
    edges=[
        ("START", planner, analyze),
        (analyze, {ROUTE_OK: explainer, ROUTE_NO_DATA: no_data, ROUTE_OUT_OF_SCOPE: out_of_scope}),
        (explainer, guardrail),
        (guardrail, {ROUTE_PASS: respond, ROUTE_RETRY: explainer, ROUTE_FALLBACK: safe_answer}),
    ],
)
