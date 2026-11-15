"""Tests for the deterministic guardrail (no LLM)."""

import pytest

from src.guardrail.checks import check_explanation, fill_placeholders, format_value


def result(zone, trend="increasing", slope=0.375, low=0.297, high=0.462, same_cell=None,
           variable="T2M", p_value=2.6e-17):
    return {
        "zone": zone, "variable": variable, "trend": trend, "significant": trend != "no trend",
        "p_value": p_value, "slope_per_decade": slope, "ci_low_per_decade": low,
        "ci_high_per_decade": high, "same_grid_cell_as": same_cell, "unit": "degC",
        "period": "1981-2024", "confidence": 0.95, "source": "NASA POWER (MERRA2)",
        "method": "seasonal Mann-Kendall test + seasonal Sen slope",
    }


@pytest.fixture
def results():
    return [
        result("napoli", same_cell="caserta"),
        result("caserta", same_cell="napoli"),
        result("salerno", slope=0.32, low=0.25, high=0.40),
        result("avellino", trend="no trend", slope=0.05, low=-0.10, high=0.20, p_value=0.4),
    ]


def claim(zone, direction="increasing"):
    return {"zone": zone, "variable": "T2M", "direction": direction}


def comparison(a, b, relation):
    return {"zone_a": a, "zone_b": b, "variable": "T2M", "relation": relation}


# A real answer produced by the explainer (gemini-3.8-flash), shortened.
GOOD_TEXT = (
    "Napoli e Caserta condividono la stessa cella di griglia, pertanto i loro dati sono identici: "
    "la temperatura è in aumento di [napoli.T2M.slope_per_decade] [napoli.T2M.unit] per decennio "
    "(intervallo tra [napoli.T2M.ci_low_per_decade] e [napoli.T2M.ci_high_per_decade]) nel periodo "
    "[napoli.T2M.period]. Anche a Salerno la temperatura è in aumento di "
    "[salerno.T2M.slope_per_decade] [salerno.T2M.unit] per decennio. Poiché gli intervalli si "
    "sovrappongono, non è possibile stabilire quale zona si scaldi più rapidamente. "
    "Dati: [napoli.T2M.source]. Metodo: [napoli.T2M.method]."
)


@pytest.fixture
def good():
    return {
        "text": GOOD_TEXT,
        "claims": [claim("napoli"), claim("caserta"), claim("salerno")],
        "comparisons": [
            comparison("napoli", "caserta", "identical_data"),
            comparison("napoli", "salerno", "not_distinguishable"),
        ],
    }


def test_good_explanation_passes(good, results):
    assert check_explanation(good, results) == []


def test_fill_placeholders(results):
    text = "[napoli.T2M.slope_per_decade] [napoli.T2M.unit] per decade, p [napoli.T2M.p_value], [napoli.T2M.confidence] CI"
    assert fill_placeholders(text, results) == "+0.375 °C per decade, p < 0.001, 95% CI"


def test_fill_leaves_invalid_placeholders(results):
    assert fill_placeholders("[roma.T2M.slope_per_decade]", results) == "[roma.T2M.slope_per_decade]"


@pytest.mark.parametrize(
    "field, value, expected",
    [("slope_per_decade", -0.1, "-0.100"), ("p_value", 0.0567, "0.057"), ("unit", "mm/day", "mm/day")],
)
def test_format_value(field, value, expected):
    assert format_value(field, value) == expected


def test_digits_written_by_the_llm(good, results):
    good["text"] += " In totale circa 1.6 gradi."
    assert any("digits" in v for v in check_explanation(good, results))


def test_unknown_placeholder_zone(good, results):
    good["text"] += " [benevento.T2M.slope_per_decade]"
    assert any("no result for benevento" in v for v in check_explanation(good, results))


def test_unknown_placeholder_field(good, results):
    good["text"] += " [napoli.T2M.lat]"
    assert any("not an allowed field" in v for v in check_explanation(good, results))


@pytest.mark.parametrize(
    "sentence",
    ["Ad Avellino la temperatura è stabile.", "The temperature is stable.",
     "L'aumento è dovuto all'urbanizzazione.", "This is due to climate change."],
)
def test_forbidden_phrases(good, results, sentence):
    good["text"] += " " + sentence
    assert any("Forbidden phrase" in v for v in check_explanation(good, results))


def test_stabilire_is_not_forbidden(good, results):
    assert "stabilire" in good["text"]
    assert check_explanation(good, results) == []


def test_wrong_direction(good, results):
    good["text"] += " Ad Avellino [avellino.T2M.slope_per_decade]."
    good["claims"].append(claim("avellino", "increasing"))  # the test says "no trend"
    violations = check_explanation(good, results)
    assert any("avellino.T2M: the text states 'increasing'" in v for v in violations)


def test_cited_result_without_claim(good, results):
    good["claims"].pop()  # salerno is still cited in the text
    assert any("salerno.T2M is cited in the text but has no claim" in v for v in check_explanation(good, results))


def test_faster_with_overlapping_intervals(good, results):
    good["comparisons"].append(comparison("napoli", "salerno", "a_faster"))
    assert any("intervals overlap" in v for v in check_explanation(good, results))


def test_faster_in_the_same_cell(good, results):
    good["comparisons"].append(comparison("napoli", "caserta", "a_faster"))
    assert any("share the same data" in v for v in check_explanation(good, results))


def test_faster_allowed_when_intervals_do_not_overlap(good, results):
    # napoli [0.297, 0.462] vs avellino [-0.10, 0.20]: no overlap, napoli has the larger slope
    good["comparisons"].append(comparison("napoli", "avellino", "a_faster"))
    assert check_explanation(good, results) == []
    good["comparisons"][-1] = comparison("napoli", "avellino", "b_faster")
    assert any("smaller slope" in v for v in check_explanation(good, results))


def test_identical_data_only_in_the_same_cell(good, results):
    good["comparisons"].append(comparison("napoli", "salerno", "identical_data"))
    assert any("different grid cells" in v for v in check_explanation(good, results))


def test_empty_text(results):
    assert check_explanation({"text": " ", "claims": [], "comparisons": []}, results) == ["The text is empty."]
