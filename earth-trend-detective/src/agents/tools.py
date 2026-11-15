"""Python tools exposed to the agents.

Rule number one: the LLM chooses WHAT to analyse (zone, variable, years);
the code decides HOW (method, significance level, data source) and computes
every number. Tools never raise: they return {"status": "error", ...} so the
agent can correct itself or explain the problem.
"""

from pathlib import Path

import numpy as np

from src.data.power import fetch_power_monthly, parse_power_monthly
from src.stats.mann_kendall import InsufficientDataError
from src.stats.seasonal import seasonal_mann_kendall, seasonal_sen_slope

DATA_RAW = Path(__file__).resolve().parents[2] / "data" / "raw"

# Fixed by us, never by the LLM.
ALPHA = 0.05
CONFIDENCE = 0.95
FIRST_YEAR, LAST_YEAR = 1981, 2024  # period downloaded and verified
MIN_YEARS = 10
METHOD = "seasonal Mann-Kendall test + seasonal Sen slope"

# Sampling zones (docs/dati.md). With NASA POWER (MERRA-2 grid) some zones share a cell.
ZONES = {
    "napoli": {"lat": 40.85, "lon": 14.27, "environment": "coast, urban", "same_cell_as": "caserta"},
    "caserta": {"lat": 41.07, "lon": 14.33, "environment": "inland plain", "same_cell_as": "napoli"},
    "salerno": {"lat": 40.68, "lon": 14.77, "environment": "southern coast", "same_cell_as": None},
    "avellino": {"lat": 40.91, "lon": 14.79, "environment": "inland Apennines", "same_cell_as": "benevento"},
    "benevento": {"lat": 41.13, "lon": 14.78, "environment": "inland hills", "same_cell_as": "avellino"},
}

VARIABLES = {
    "T2M": {"name": "air temperature at 2 m", "unit": "degC"},
    "PRECTOTCORR": {"name": "precipitation (corrected)", "unit": "mm/day"},
}


def _error(message: str) -> dict:
    return {"status": "error", "message": message}


def _round_sig(x: float, digits: int = 3) -> float:
    """Round to significant digits, so tiny p-values do not become 0."""
    return float(f"{x:.{digits}g}")


def analyze_trend(
    zone: str,
    variable: str,
    start_year: int = FIRST_YEAR,
    end_year: int = LAST_YEAR,
) -> dict:
    """Test whether a climate variable has a statistically significant trend in a zone of Campania (Italy).

    Uses monthly NASA POWER data and a seasonal Mann-Kendall test (each month is compared
    only with the same month of other years), with the seasonal Sen slope and its 95%
    confidence interval. The significance level is fixed at 0.05.

    Args:
        zone: one of "napoli", "caserta", "salerno", "avellino", "benevento".
        variable: "T2M" (air temperature at 2 m, degC) or "PRECTOTCORR" (precipitation, mm/day).
        start_year: first year to include, from 1981.
        end_year: last year to include, up to 2024. At least 10 years are required.

    Returns:
        A dict with status "success" and the computed numbers (trend direction, p-value,
        slope per decade with confidence interval, number of observations, data source),
        or status "error" with a message explaining what to change.
    """
    zone = zone.strip().lower()
    variable = variable.strip().upper()
    if zone not in ZONES:
        return _error(f"Unknown zone '{zone}'. Available zones: {', '.join(ZONES)}.")
    if variable not in VARIABLES:
        return _error(f"Unknown variable '{variable}'. Available variables: {', '.join(VARIABLES)}.")
    if not (FIRST_YEAR <= start_year <= end_year <= LAST_YEAR):
        return _error(f"Years must satisfy {FIRST_YEAR} <= start_year <= end_year <= {LAST_YEAR}.")
    if end_year - start_year + 1 < MIN_YEARS:
        return _error(f"At least {MIN_YEARS} years are needed to test for a trend.")

    info = ZONES[zone]
    try:
        # Always the full verified period, cached per zone; the years are filtered below.
        payload = fetch_power_monthly(
            info["lat"], info["lon"], FIRST_YEAR, LAST_YEAR, DATA_RAW / f"power_monthly_{zone}.json"
        )
    except Exception as e:  # network errors, HTTP errors
        return _error(f"Could not download NASA POWER data: {type(e).__name__}: {e}")

    df = parse_power_monthly(payload, zone)
    df = df[(df["variable"] == variable) & df["date"].dt.year.between(start_year, end_year)]
    years = df["date"].dt.year.to_numpy()
    months = df["date"].dt.month.to_numpy()
    values = df["value"].to_numpy(dtype=float)

    try:
        mk = seasonal_mann_kendall(years, months, values, alpha=ALPHA)
        sen = seasonal_sen_slope(years, months, values, confidence=CONFIDENCE)
    except InsufficientDataError as e:
        return _error(f"Insufficient data: {e}")

    return {
        "status": "success",
        "zone": zone,
        "environment": info["environment"],
        "lat": info["lat"],
        "lon": info["lon"],
        "same_grid_cell_as": info["same_cell_as"],
        "variable": variable,
        "variable_name": VARIABLES[variable]["name"],
        "unit": VARIABLES[variable]["unit"],
        "period": f"{start_year}-{end_year}",
        "method": METHOD,
        "alpha": ALPHA,
        "trend": mk.trend,
        "significant": mk.significant,
        "p_value": _round_sig(mk.p_value),
        "slope_per_decade": round(sen.slope * 10, 3),
        "ci_low_per_decade": round(sen.lower * 10, 3),
        "ci_high_per_decade": round(sen.upper * 10, 3),
        "confidence": CONFIDENCE,
        "n_months": mk.n,
        "n_missing": mk.n_missing,
        "mean_value": round(float(np.nanmean(values)), 2),
        "source": df["source"].iloc[0],
    }
