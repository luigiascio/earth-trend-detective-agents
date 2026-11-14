"""Read NASA POWER monthly point responses into the internal long-format schema."""

import math
from datetime import date

import pandas as pd

# POWER puts the annual mean under month "13" (e.g. "198113").
ANNUAL_MONTH = 13

COLUMNS = ["date", "value", "variable", "unit", "lat", "lon", "zone", "source"]


def _parse_month_key(key: str) -> date | None:
    """Turn a POWER key "YYYYMM" into the first day of that month.

    Returns None for the annual mean (month 13), which must be dropped.
    """
    year, month = int(key[:4]), int(key[4:])
    if month == ANNUAL_MONTH:
        return None
    return date(year, month, 1)


def parse_power_monthly(payload: dict, zone: str) -> pd.DataFrame:
    """Convert a NASA POWER monthly point response into a long-format table.

    Drops the annual means (month "13") and turns fill values into NaN.

    Args:
        payload: the parsed JSON returned by the POWER monthly point API.
        zone: label of the sampling zone, e.g. "napoli".

    Returns:
        One row per (month, variable) with columns
        date, value, variable, unit, lat, lon, zone, source.
    """
    header = payload["header"]
    fill_value = header["fill_value"]
    source = "NASA POWER (" + ", ".join(header["sources"]) + ")"
    # GeoJSON order: longitude first, then latitude, then elevation.
    lon, lat = payload["geometry"]["coordinates"][:2]

    rows = []
    for variable, series in payload["properties"]["parameter"].items():
        unit = payload["parameters"][variable]["units"]
        for key, value in series.items():
            month_start = _parse_month_key(key)
            if month_start is None:
                continue
            rows.append(
                {
                    "date": month_start,
                    # Missing data stays explicit: never fill it silently.
                    "value": math.nan if value == fill_value else float(value),
                    "variable": variable,
                    "unit": unit,
                    "lat": lat,
                    "lon": lon,
                    "zone": zone,
                    "source": source,
                }
            )

    df = pd.DataFrame(rows, columns=COLUMNS)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["variable", "date"], ignore_index=True)
