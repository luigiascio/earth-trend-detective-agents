"""Deterministic guardrail: check the explanation against the computed results.

Pure functions, no LLM. See docs/guardrail.md.
"""

import re

PLACEHOLDER = re.compile(r"\[([a-z]+)\.([A-Z0-9]+)\.([a-z_]+)\]")

# Fields of a result that the explanation may cite as [zone.variable.field].
PLACEHOLDER_FIELDS = (
    "slope_per_decade", "ci_low_per_decade", "ci_high_per_decade", "p_value", "q_value", "n_tests",
    "period", "unit", "mean_value", "n_months", "confidence", "alpha", "source", "method",
)

# Words that break the interpretation rules (docs/statistica.md) or attribute causes
# (docs/guardrail.md). English and Italian, regular expressions matched on lowercase text
# with word boundaries (so "stabilire" is not mistaken for "stabile").
FORBIDDEN_PHRASES = (
    r"\bstable\b", r"\bstability\b", r"\bunchanged\b", r"\bnot changing\b", r"\bno change\b",
    r"\bstabil[ei]\b", r"\bstabilità\b", r"\binvariat[aoei]\b", r"\bnon cambia\b",
    r"\bnessun cambiamento\b",
    r"\bbecause of\b", r"\bdue to\b", r"\bcaused by\b",
    r"\ba causa d", r"\bdovut[aoei]\b", r"\bcausat[aoei]\b",
)

UNITS = {"degC": "°C", "mm/day": "mm/day"}


def format_value(field: str, value) -> str:
    """How each field is written in the final text (the only place numbers are formatted)."""
    if field == "slope_per_decade":
        return f"{value:+.3f}"
    if field in ("ci_low_per_decade", "ci_high_per_decade"):
        return f"{value:.3f}"
    if field in ("p_value", "q_value"):
        return "< 0.001" if value < 0.001 else f"{value:.3f}"
    if field == "confidence":
        return f"{value:.0%}"
    if field == "unit":
        return UNITS.get(value, value)
    return str(value)


def _index(results: list[dict]) -> dict[tuple[str, str], dict]:
    return {(r["zone"], r["variable"]): r for r in results}


def fill_placeholders(text: str, results: list[dict]) -> str:
    """Replace every valid placeholder with its formatted value; leave invalid ones as they are."""
    by_key = _index(results)

    def replace(match: re.Match) -> str:
        zone, variable, field = match.groups()
        result = by_key.get((zone, variable))
        if result is None or field not in PLACEHOLDER_FIELDS:
            return match.group(0)
        return format_value(field, result[field])

    return PLACEHOLDER.sub(replace, text)


def _intervals_overlap(a: dict, b: dict) -> bool:
    return a["ci_low_per_decade"] <= b["ci_high_per_decade"] and b["ci_low_per_decade"] <= a["ci_high_per_decade"]


def check_explanation(explanation: dict, results: list[dict]) -> list[str]:
    """Return the list of violations (empty list = the explanation passes).

    Each message is written for the explainer, which gets it back on a retry.
    """
    violations = []
    by_key = _index(results)
    text = explanation.get("text", "")

    if not text.strip():
        return ["The text is empty."]

    # 1. Placeholders must point to an existing result and an allowed field.
    cited = set()
    for zone, variable, field in PLACEHOLDER.findall(text):
        if (zone, variable) not in by_key:
            violations.append(f"Placeholder [{zone}.{variable}.{field}]: there is no result for {zone}.{variable}.")
        elif field not in PLACEHOLDER_FIELDS:
            violations.append(f"Placeholder [{zone}.{variable}.{field}]: '{field}' is not an allowed field.")
        else:
            cited.add((zone, variable))

    # 2. No number written by the LLM: no digits outside placeholders.
    without_placeholders = PLACEHOLDER.sub("", text)
    if re.search(r"\d", without_placeholders):
        violations.append("The text contains digits outside placeholders: write every number as a placeholder.")

    # 3. Forbidden phrases.
    lowered = text.lower()
    for pattern in FORBIDDEN_PHRASES:
        match = re.search(pattern, lowered)
        if match:
            violations.append(
                f"Forbidden phrase '{match.group(0)}': do not call a variable stable or unchanged, "
                "and do not attribute causes."
            )

    # 4. Claims: one per cited result, with the computed direction.
    claimed = set()
    for claim in explanation.get("claims", []):
        key = (claim["zone"], claim["variable"])
        claimed.add(key)
        result = by_key.get(key)
        if result is None:
            violations.append(f"Claim about {key[0]}.{key[1]}, but there is no such result.")
        elif claim["direction"] != result["trend"]:
            violations.append(
                f"{key[0]}.{key[1]}: the text states '{claim['direction']}' but the test says "
                f"'{result['trend']}' (significant={result['significant']})."
            )
    for zone, variable in sorted(cited - claimed):
        violations.append(f"{zone}.{variable} is cited in the text but has no claim.")

    # 5. Comparisons between zones.
    for comp in explanation.get("comparisons", []):
        a = by_key.get((comp["zone_a"], comp["variable"]))
        b = by_key.get((comp["zone_b"], comp["variable"]))
        name = f"{comp['zone_a']} vs {comp['zone_b']} ({comp['variable']})"
        if a is None or b is None:
            violations.append(f"Comparison {name}: one of the two results does not exist.")
            continue
        same_cell = a["same_grid_cell_as"] == b["zone"]
        relation = comp["relation"]
        if relation == "identical_data" and not same_cell:
            violations.append(f"Comparison {name}: the two zones are in different grid cells, their data are not identical.")
        elif relation in ("a_faster", "b_faster"):
            faster, slower = (a, b) if relation == "a_faster" else (b, a)
            if same_cell:
                violations.append(f"Comparison {name}: the two zones share the same data and cannot be compared.")
            elif _intervals_overlap(a, b):
                violations.append(f"Comparison {name}: the confidence intervals overlap, so neither zone can be called faster.")
            elif abs(faster["slope_per_decade"]) <= abs(slower["slope_per_decade"]):
                violations.append(f"Comparison {name}: the zone called faster has the smaller slope.")
        elif relation == "not_distinguishable" and same_cell:
            violations.append(f"Comparison {name}: say that the two zones share the same data.")

    return violations
