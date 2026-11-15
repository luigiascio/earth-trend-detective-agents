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
