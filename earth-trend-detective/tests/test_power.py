import json

import numpy as np
import pandas as pd
import pytest

from src.data.power import COLUMNS, fetch_power_monthly, parse_power_monthly


def make_payload(t2m: dict, prec: dict | None = None) -> dict:
    """A minimal POWER-like response, written by hand (no network needed)."""
    parameter = {"T2M": t2m}
    parameters = {"T2M": {"units": "C", "longname": "Temperature at 2 Meters"}}
    if prec is not None:
        parameter["PRECTOTCORR"] = prec
        parameters["PRECTOTCORR"] = {"units": "mm/day", "longname": "Precipitation Corrected"}
    return {
        "geometry": {"coordinates": [14.27, 40.85, 264.43]},  # lon, lat, elevation
        "properties": {"parameter": parameter},
        "parameters": parameters,
        "header": {"fill_value": -999.0, "sources": ["MERRA2"]},
    }


def test_columns_follow_the_internal_schema():
    df = parse_power_monthly(make_payload({"198101": 8.0}), "napoli")
    assert list(df.columns) == COLUMNS


def test_annual_mean_is_dropped():
    df = parse_power_monthly(make_payload({"198101": 8.0, "198102": 9.0, "198113": 15.0}), "napoli")
    assert len(df) == 2
    assert 15.0 not in df["value"].tolist()


def test_dates_are_first_day_of_month():
    df = parse_power_monthly(make_payload({"198102": 9.0, "198112": 10.0}), "napoli")
    assert df["date"].tolist() == [pd.Timestamp("1981-02-01"), pd.Timestamp("1981-12-01")]


def test_fill_value_becomes_nan():
    df = parse_power_monthly(make_payload({"198101": 8.0, "198102": -999.0}), "napoli")
    assert df["value"].isna().sum() == 1
    assert -999.0 not in df["value"].tolist()


def test_longitude_and_latitude_are_not_swapped():
    df = parse_power_monthly(make_payload({"198101": 8.0}), "napoli")
    assert df["lat"].iloc[0] == 40.85
    assert df["lon"].iloc[0] == 14.27


def test_metadata_on_every_row():
    df = parse_power_monthly(
        make_payload({"198101": 8.0, "198102": 9.0}, {"198101": 3.1, "198102": 2.0}), "napoli"
    )
    assert len(df) == 4
    assert set(df["variable"]) == {"T2M", "PRECTOTCORR"}
    assert df.loc[df["variable"] == "T2M", "unit"].unique().tolist() == ["C"]
    assert df.loc[df["variable"] == "PRECTOTCORR", "unit"].unique().tolist() == ["mm/day"]
    assert (df["zone"] == "napoli").all()
    assert (df["source"] == "NASA POWER (MERRA2)").all()


def test_fetch_uses_cache_without_network(tmp_path, monkeypatch):
    # If the cache file exists, requests.get must never be called.
    payload = make_payload({"198101": 8.0})
    cache_file = tmp_path / "cached.json"
    cache_file.write_text(json.dumps(payload), encoding="utf-8")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("network was called despite the cache")

    monkeypatch.setattr("src.data.power.requests.get", fail_if_called)
    assert fetch_power_monthly(40.85, 14.27, 1981, 1981, cache_file) == payload


def test_real_file_if_downloaded():
    # Runs only if the Naples file from the morning check is on disk (data/ is not on git).
    path = "data/raw/power_monthly_napoli.json"
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    except FileNotFoundError:
        pytest.skip(f"{path} not downloaded")
    df = parse_power_monthly(payload, "napoli")
    assert len(df) == 2 * 528  # 44 years x 12 months x 2 variables
    assert not np.any(df["date"].dt.month > 12)
