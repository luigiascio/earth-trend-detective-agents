import numpy as np
import pytest

from src.agents import tools
from src.agents.tools import ZONES, analyze_trend


def synthetic_payload(slope_per_year: float = 0.03) -> dict:
    """A POWER-like response for 1981-2024 with a seasonal cycle and a known trend."""
    rng = np.random.default_rng(0)
    series = {}
    for year in range(1981, 2025):
        for month in range(1, 13):
            value = 15 + 8 * np.sin(2 * np.pi * (month - 4) / 12) + slope_per_year * (year - 1981)
            series[f"{year}{month:02d}"] = round(float(value + rng.normal(0, 0.3)), 2)
        series[f"{year}13"] = 15.0  # annual mean, must be ignored
    return {
        "geometry": {"coordinates": [14.27, 40.85, 264.43]},
        "properties": {"parameter": {"T2M": series}},
        "parameters": {"T2M": {"units": "C", "longname": "Temperature at 2 Meters"}},
        "header": {"fill_value": -999.0, "sources": ["MERRA2"]},
    }


@pytest.fixture
def fake_power(monkeypatch):
    """Replace the download with a synthetic payload: no network, no files."""
    monkeypatch.setattr(tools, "fetch_power_monthly", lambda *args, **kwargs: synthetic_payload())


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({"zone": "paris", "variable": "T2M"}, "Unknown zone"),
        ({"zone": "napoli", "variable": "NDVI"}, "Unknown variable"),
        ({"zone": "napoli", "variable": "T2M", "start_year": 1970}, "Years must satisfy"),
        ({"zone": "napoli", "variable": "T2M", "end_year": 2030}, "Years must satisfy"),
        ({"zone": "napoli", "variable": "T2M", "start_year": 2010, "end_year": 2000}, "Years must satisfy"),
        ({"zone": "napoli", "variable": "T2M", "start_year": 2020}, "At least 10 years"),
    ],
)
def test_invalid_requests_return_an_error_instead_of_raising(kwargs, expected):
    result = analyze_trend(**kwargs)
    assert result["status"] == "error"
    assert expected in result["message"]


def test_zone_and_variable_are_case_insensitive(fake_power):
    assert analyze_trend(" Napoli ", "t2m")["status"] == "success"


def test_success_contains_the_numbers_from_the_statistics(fake_power):
    result = analyze_trend("napoli", "T2M")
    assert result["status"] == "success"
    assert result["trend"] == "increasing"
    assert result["significant"] is True
    assert result["slope_per_decade"] == pytest.approx(0.3, abs=0.05)
    assert result["ci_low_per_decade"] <= result["slope_per_decade"] <= result["ci_high_per_decade"]
    assert result["n_months"] == 44 * 12
    assert result["period"] == "1981-2024"
    assert result["alpha"] == 0.05
    assert result["source"] == "NASA POWER (MERRA2)"
    assert result["same_grid_cell_as"] is None  # every zone has its own grid cell


def test_years_filter_the_series(fake_power):
    result = analyze_trend("napoli", "T2M", start_year=2000, end_year=2024)
    assert result["n_months"] == 25 * 12
    assert result["period"] == "2000-2024"


def test_tiny_p_value_is_not_rounded_to_zero(fake_power):
    assert 0 < analyze_trend("napoli", "T2M")["p_value"] < 1e-6


def test_download_failure_returns_an_error(monkeypatch):
    def broken(*args, **kwargs):
        raise ConnectionError("no network")

    monkeypatch.setattr(tools, "fetch_power_monthly", broken)
    result = analyze_trend("napoli", "T2M")
    assert result["status"] == "error"
    assert "no network" in result["message"]


def test_contract_zones_match_the_tool_zones():
    """The planner's closed list (contracts.Zone) must be exactly the zones the tool knows."""
    from typing import get_args

    from src.contracts import Zone

    assert set(get_args(Zone)) == set(ZONES)


def test_zone_names_fit_the_placeholder_syntax():
    """Zone names appear in placeholders [zone.variable.field]: lowercase letters only."""
    assert all(name.isalpha() and name.islower() for name in ZONES)
