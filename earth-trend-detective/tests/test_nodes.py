"""Tests for the Python nodes of the workflow graph (no LLM, no network)."""

import pytest

from src.agents import nodes


def item(zone, variable="T2M", start_year=1981, end_year=2024):
    return {"zone": zone, "variable": variable, "start_year": start_year, "end_year": end_year}


@pytest.fixture
def fake_trend(monkeypatch):
    """Replace analyze_trend: 'salerno' fails, every other zone succeeds. Records the calls."""
    calls = []

    def fake(zone, variable, start_year, end_year):
        calls.append((zone, variable, start_year, end_year))
        if zone == "salerno":
            return {"status": "error", "message": "NASA POWER did not answer"}
        return {"status": "success", "zone": zone, "variable": variable}

    monkeypatch.setattr(nodes, "analyze_trend", fake)
    return calls


def test_all_analyses_succeed(fake_trend):
    event = nodes.analyze({"out_of_scope": False, "items": [item("napoli"), item("avellino")]})
    assert event.actions.route == nodes.ROUTE_OK
    assert [r["zone"] for r in event.actions.state_delta["results"]] == ["napoli", "avellino"]
    assert event.actions.state_delta["errors"] == []


def test_partial_failure_keeps_valid_results(fake_trend):
    event = nodes.analyze({"items": [item("napoli"), item("salerno")]})
    state = event.actions.state_delta
    assert event.actions.route == nodes.ROUTE_OK
    assert [r["zone"] for r in state["results"]] == ["napoli"]
    assert state["errors"] == [{**item("salerno"), "message": "NASA POWER did not answer"}]


def test_all_analyses_fail(fake_trend):
    event = nodes.analyze({"items": [item("salerno")]})
    assert event.actions.route == nodes.ROUTE_NO_DATA
    assert event.actions.state_delta["results"] == []


@pytest.mark.parametrize(
    "plan",
    [
        {"out_of_scope": True, "reason": "Rome", "items": []},
        {"out_of_scope": True, "items": [item("napoli")]},  # flag wins even if items are present
        {"out_of_scope": False, "items": []},
    ],
)
def test_out_of_scope_runs_nothing(fake_trend, plan):
    event = nodes.analyze(plan)
    assert event.actions.route == nodes.ROUTE_OUT_OF_SCOPE
    assert fake_trend == []


def test_repeated_items_are_computed_once(fake_trend):
    nodes.analyze({"items": [item("napoli"), item("napoli"), item("napoli", "PRECTOTCORR")]})
    assert fake_trend == [("napoli", "T2M", 1981, 2024), ("napoli", "PRECTOTCORR", 1981, 2024)]


# --- guardrail and final answers -------------------------------------------------

from types import SimpleNamespace  # noqa: E402

RESULT = {
    "zone": "salerno", "variable": "T2M", "variable_name": "air temperature at 2 m",
    "trend": "increasing", "significant": True, "p_value": 1e-8, "q_value": 2e-8, "n_tests": 20,
    "region": "Campania", "slope_per_decade": 0.32,
    "ci_low_per_decade": 0.25, "ci_high_per_decade": 0.397, "same_grid_cell_as": None,
    "unit": "degC", "period": "1981-2024", "confidence": 0.95, "alpha": 0.05,
    "source": "NASA POWER (MERRA2)", "method": "seasonal Mann-Kendall test + seasonal Sen slope",
}
GOOD = {
    "text": "A Salerno aumento di [salerno.T2M.slope_per_decade] [salerno.T2M.unit] per decennio.",
    "claims": [{"zone": "salerno", "variable": "T2M", "direction": "increasing"}],
    "comparisons": [],
}
BAD = {**GOOD, "text": GOOD["text"] + " Circa 1 grado in totale."}


def ctx_with(attempts):
    return SimpleNamespace(state={"guardrail_attempts": attempts})


def test_guardrail_pass_fills_placeholders():
    event = nodes.guardrail(GOOD, [RESULT], ctx_with(0))
    assert event.actions.route == nodes.ROUTE_PASS
    assert event.actions.state_delta["answer"] == "A Salerno aumento di +0.320 °C per decennio."


def test_guardrail_retry_passes_feedback():
    event = nodes.guardrail(BAD, [RESULT], ctx_with(0))
    assert event.actions.route == nodes.ROUTE_RETRY
    assert event.actions.state_delta["guardrail_attempts"] == 1
    assert any("digits" in v for v in event.actions.state_delta["guardrail_feedback"])


def test_guardrail_fallback_after_max_attempts():
    event = nodes.guardrail(BAD, [RESULT], ctx_with(nodes.MAX_ATTEMPTS - 1))
    assert event.actions.route == nodes.ROUTE_FALLBACK
    assert event.actions.state_delta["guardrail_report"]["passed"] is False


def test_safe_answer_uses_true_numbers():
    error = {"zone": "napoli", "variable": "T2M", "message": "timeout"}
    text = nodes.safe_answer([RESULT], [error]).actions.state_delta["answer"]
    assert "statistically significant increasing trend (+0.320 °C per decade, 95% CI 0.250 to 0.397, q-value < 0.001)" in text
    assert "Napoli, T2M: data not available (timeout)" in text


def test_analyze_resets_previous_question(fake_trend):
    state = nodes.analyze({"items": [item("napoli")]}).actions.state_delta
    assert state["guardrail_attempts"] == 0 and state["guardrail_feedback"] == []


def test_plan_is_capped(fake_trend, monkeypatch):
    monkeypatch.setattr(nodes, "MAX_ANALYSES", 2)
    state = nodes.analyze({"items": [item("napoli"), item("roma"), item("bari")]}).actions.state_delta
    assert len(state["results"]) == 2
    assert state["errors"][0]["zone"] == "bari" and "at most 2" in state["errors"][0]["message"]
