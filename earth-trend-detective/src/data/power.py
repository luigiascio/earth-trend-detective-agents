"""Read NASA POWER monthly point responses into the internal long-format schema."""

import json
import math
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

POWER_MONTHLY_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"

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


def fetch_power_monthly(
    lat: float,
    lon: float,
    start_year: int,
    end_year: int,
    cache_file: Path,
    parameters: tuple[str, ...] = ("T2M", "PRECTOTCORR"),
    max_attempts: int = 3,
) -> dict:
    """Download a NASA POWER monthly point series, using a local cache.

    Returns the parsed JSON (the same dict that parse_power_monthly expects).
    Retries only on timeouts and connection errors; HTTP errors are raised at once.
    """
    cache_file = Path(cache_file)

    # 1. Cache: never download the same series twice.
    if cache_file.exists():
        with cache_file.open(encoding="utf-8") as f:
            return json.load(f)

    # 2. Request parameters (requests builds the "?key=value&..." part of the URL).
    params = {
        "parameters": ",".join(parameters),
        "community": "AG",
        "latitude": lat,
        "longitude": lon,
        "start": start_year,
        "end": end_year,
        "format": "JSON",
    }

    # 3. Download with retries and exponential backoff (1 s, 2 s, 4 s, ...).
    for attempt in range(max_attempts):
        try:
            response = requests.get(POWER_MONTHLY_URL, params=params, timeout=180)
            response.raise_for_status()
            break
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            if attempt == max_attempts - 1:
                raise
            time.sleep(2**attempt)

    # 4. Save the raw response to the cache, then return it.
    payload = response.json()
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with cache_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f)
    return payload