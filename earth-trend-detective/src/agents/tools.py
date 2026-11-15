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
from src.stats.multiple import benjamini_hochberg
from src.stats.seasonal import seasonal_mann_kendall, seasonal_sen_slope

DATA_RAW = Path(__file__).resolve().parents[2] / "data" / "raw"

# Fixed by us, never by the LLM.
ALPHA = 0.05
CONFIDENCE = 0.95
FIRST_YEAR, LAST_YEAR = 1981, 2024  # period downloaded and verified
MIN_YEARS = 10
METHOD = "seasonal Mann-Kendall test + seasonal Sen slope, Benjamini-Hochberg correction across zones"

# Sampling zones: the 20 regional capitals of Italy (docs/dati.md). Names must be lowercase
# letters only (they are used in placeholders). Verified 2026-11-15: all 20 zones have
# different NASA POWER series, i.e. no two zones share a MERRA-2 grid cell. If a zone is added
# in the same cell as another, set "same_cell_as" so the app says their data are identical.
def _zone(lat: float, lon: float, region: str, environment: str) -> dict:
    return {"lat": lat, "lon": lon, "region": region, "environment": environment, "same_cell_as": None}


ZONES = {
    "aosta": _zone(45.74, 7.32, "Valle d'Aosta", "north, western Alps, mountain valley"),
    "torino": _zone(45.07, 7.69, "Piemonte", "north, foot of the western Alps, Po Valley, urban"),
    "milano": _zone(45.46, 9.19, "Lombardia", "north, Po Valley, inland plain, urban"),
    "trento": _zone(46.07, 11.12, "Trentino-Alto Adige", "north, eastern Alps, mountain valley"),
    "venezia": _zone(45.44, 12.33, "Veneto", "north, Adriatic coast"),
    "trieste": _zone(45.65, 13.78, "Friuli-Venezia Giulia", "north-east, Adriatic coast"),
    "genova": _zone(44.41, 8.93, "Liguria", "north, Ligurian coast"),
    "bologna": _zone(44.49, 11.34, "Emilia-Romagna", "north, Po Valley, foot of the Apennines, urban"),
    "firenze": _zone(43.77, 11.25, "Toscana", "centre, inland hills"),
    "perugia": _zone(43.11, 12.39, "Umbria", "centre, inland hills"),
    "ancona": _zone(43.62, 13.52, "Marche", "centre, Adriatic coast"),
    "roma": _zone(41.90, 12.50, "Lazio", "centre, near the Tyrrhenian coast, urban"),
    "aquila": _zone(42.35, 13.40, "Abruzzo", "centre, L'Aquila, Apennine mountains"),
    "campobasso": _zone(41.56, 14.66, "Molise", "south, Apennine hills"),
    "napoli": _zone(40.85, 14.27, "Campania", "south, Tyrrhenian coast, urban"),
    "bari": _zone(41.12, 16.87, "Puglia", "south, Adriatic coast"),
    "potenza": _zone(40.64, 15.80, "Basilicata", "south, Apennine mountains"),
    "catanzaro": _zone(38.91, 16.59, "Calabria", "south, between two seas, hills"),
    "palermo": _zone(38.12, 13.36, "Sicilia", "islands, Sicily, coast"),
    "cagliari": _zone(39.22, 9.12, "Sardegna", "islands, Sardinia, coast"),
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


def _load_series(zone: str, variable: str, start_year: int, end_year: int):
    """Monthly series of one zone (downloads on first use, then local cache). May raise."""
    info = ZONES[zone]
    # Always the full verified period, cached per zone; the years are filtered here.
    payload = fetch_power_monthly(
        info["lat"], info["lon"], FIRST_YEAR, LAST_YEAR, DATA_RAW / f"power_monthly_{zone}.json"
    )
    df = parse_power_monthly(payload, zone)
    return df[(df["variable"] == variable) & df["date"].dt.year.between(start_year, end_year)]


def _arrays(df):
    return (df["date"].dt.year.to_numpy(), df["date"].dt.month.to_numpy(),
            df["value"].to_numpy(dtype=float))


# The family of tests for the Benjamini-Hochberg correction: all zones, same variable and
# period. Fixed, so a trend gets the same verdict whatever else the user asks about.
_FAMILY_CACHE: dict[tuple[str, int, int], dict[str, float]] = {}


def family_q_values(variable: str, start_year: int, end_year: int) -> dict[str, float]:
    """Benjamini-Hochberg q-values of the seasonal Mann-Kendall test for every zone.

    Zones whose data cannot be loaded or are too short are left out of the family.
    """
    key = (variable, start_year, end_year)
    if key not in _FAMILY_CACHE:
        p_values = {}
        for zone in ZONES:
            try:
                p_values[zone] = seasonal_mann_kendall(*_arrays(_load_series(zone, variable, start_year, end_year))).p_value
            except Exception:  # download error or insufficient data: not part of the family
                continue
        q = benjamini_hochberg(list(p_values.values()))
        _FAMILY_CACHE[key] = dict(zip(p_values, (float(v) for v in q)))
    return _FAMILY_CACHE[key]


def analyze_trend(
    zone: str,
    variable: str,
    start_year: int = FIRST_YEAR,
    end_year: int = LAST_YEAR,
) -> dict:
    """Test whether a climate variable has a statistically significant trend in a zone of Italy.

    Uses monthly NASA POWER data and a seasonal Mann-Kendall test (each month is compared
    only with the same month of other years), with the seasonal Sen slope and its 95%
    confidence interval. Significance is decided on the Benjamini-Hochberg q-value, which
    corrects the p-value for testing all zones (same variable and period), at level 0.05.

    Args:
        zone: one of the keys of ZONES (e.g. "aosta", "milano", "napoli", "palermo").
        variable: "T2M" (air temperature at 2 m, degC) or "PRECTOTCORR" (precipitation, mm/day).
        start_year: first year to include, from 1981.
        end_year: last year to include, up to 2024. At least 10 years are required.

    Returns:
        A dict with status "success" and the computed numbers (trend direction, p-value, q-value,
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
        df = _load_series(zone, variable, start_year, end_year)
    except Exception as e:  # network errors, HTTP errors
        return _error(f"Could not download NASA POWER data: {type(e).__name__}: {e}")
    years, months, values = _arrays(df)

    try:
        mk = seasonal_mann_kendall(years, months, values, alpha=ALPHA)
        sen = seasonal_sen_slope(years, months, values, confidence=CONFIDENCE)
    except InsufficientDataError as e:
        return _error(f"Insufficient data: {e}")

    # Significance after the correction for multiple tests across zones (q-value).
    family = family_q_values(variable, start_year, end_year)
    q_value = family.get(zone, mk.p_value)
    significant = q_value < ALPHA
    trend = mk.trend if significant else "no trend"  # q >= p, so significant here implies mk.significant

    return {
        "status": "success",
        "zone": zone,
        "region": info["region"],
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
        "trend": trend,
        "significant": significant,
        "p_value": _round_sig(mk.p_value),
        "q_value": _round_sig(q_value),
        "n_tests": len(family),
        "slope_per_decade": round(sen.slope * 10, 3),
        "ci_low_per_decade": round(sen.lower * 10, 3),
        "ci_high_per_decade": round(sen.upper * 10, 3),
        "confidence": CONFIDENCE,
        "n_months": mk.n,
        "n_missing": mk.n_missing,
        "mean_value": round(float(np.nanmean(values)), 2),
        "source": df["source"].iloc[0],
    }
