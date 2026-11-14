import numpy as np
import pymannkendall as pmk
import pytest

from src.stats.mann_kendall import InsufficientDataError, mann_kendall_test
from src.stats.seasonal import seasonal_mann_kendall, seasonal_sen_slope, trends_by_month


def monthly_series(n_years=44, slope_per_year=0.0, amplitude=8.0, noise=1.0, seed=0):
    """Synthetic monthly temperatures: seasonal cycle + linear trend + noise."""
    rng = np.random.default_rng(seed)
    years = np.repeat(np.arange(1981, 1981 + n_years), 12)
    months = np.tile(np.arange(1, 13), n_years)
    cycle = amplitude * np.sin(2 * np.pi * (months - 4) / 12)  # peak in July
    trend = slope_per_year * (years - years[0])
    values = np.round(15 + cycle + trend + rng.normal(0, noise, len(years)), 2)
    return years, months, values


@pytest.mark.parametrize("seed", [1, 2, 3])
@pytest.mark.parametrize("slope", [0.0, 0.02, -0.03])
def test_matches_pymannkendall(seed, slope):
    years, months, values = monthly_series(slope_per_year=slope, seed=seed)
    ours = seasonal_mann_kendall(years, months, values)
    ref = pmk.seasonal_test(values, period=12)
    assert ours.s == ref.s
    assert ours.var_s == pytest.approx(ref.var_s)
    assert ours.z == pytest.approx(ref.z)
    assert ours.p_value == pytest.approx(ref.p, abs=1e-12)
    assert ours.tau == pytest.approx(ref.Tau)
    assert seasonal_sen_slope(years, months, values).slope == pytest.approx(
        pmk.seasonal_sens_slope(values, period=12).slope
    )


def test_order_of_rows_does_not_matter():
    years, months, values = monthly_series(slope_per_year=0.02, seed=4)
    shuffle = np.random.default_rng(0).permutation(len(values))
    a = seasonal_mann_kendall(years, months, values)
    b = seasonal_mann_kendall(years[shuffle], months[shuffle], values[shuffle])
    assert a == b


def test_seasonal_test_sees_through_the_annual_cycle():
    # The problem found in step 3: the annual cycle swamps a real trend in the plain test.
    years, months, values = monthly_series(slope_per_year=0.02, amplitude=10, noise=0.5, seed=5)
    plain = mann_kendall_test(values)
    seasonal = seasonal_mann_kendall(years, months, values)
    assert seasonal.trend == "increasing"
    assert seasonal.z > 3 * plain.z


def test_pure_seasonal_cycle_is_not_a_trend():
    years, months, values = monthly_series(slope_per_year=0.0, amplitude=10, seed=6)
    assert seasonal_mann_kendall(years, months, values).trend == "no trend"
    sen = seasonal_sen_slope(years, months, values)
    assert sen.lower <= 0 <= sen.upper


def test_recovers_known_slope():
    true_slope = 0.035
    years, months, values = monthly_series(slope_per_year=true_slope, noise=0.5, seed=7)
    sen = seasonal_sen_slope(years, months, values)
    assert sen.slope == pytest.approx(true_slope, abs=0.005)
    assert sen.lower <= true_slope <= sen.upper


def test_missing_values_are_dropped_and_counted():
    years, months, values = monthly_series(slope_per_year=0.03, seed=8)
    values = values.astype(float)
    values[[0, 100, 200]] = np.nan
    result = seasonal_mann_kendall(years, months, values)
    assert result.n == 44 * 12 - 3
    assert result.n_missing == 3
    assert seasonal_sen_slope(years, months, values).n_missing == 3


def test_too_few_years_raises():
    years, months, values = monthly_series(n_years=5)
    with pytest.raises(InsufficientDataError):
        seasonal_mann_kendall(years, months, values)
    with pytest.raises(InsufficientDataError):
        seasonal_sen_slope(years, months, values)


def test_inputs_must_have_same_length():
    years, months, values = monthly_series()
    with pytest.raises(ValueError):
        seasonal_mann_kendall(years, months[:-1], values)


def test_trends_by_month_returns_one_result_per_month():
    years, months, values = monthly_series(slope_per_year=0.03, noise=0.3, seed=9)
    by_month = trends_by_month(years, months, values)
    assert [t.month for t in by_month] == list(range(1, 13))
    for t in by_month:
        assert t.mann_kendall.n == 44
        assert t.sen.slope == pytest.approx(0.03, abs=0.01)


def test_trends_by_month_finds_the_month_that_warms():
    # Only July warms: July must come out increasing, January must not.
    years, months, values = monthly_series(slope_per_year=0.0, noise=0.3, seed=10)
    values = values + np.where(months == 7, 0.05 * (years - years[0]), 0.0)
    by_month = {t.month: t for t in trends_by_month(years, months, values)}
    assert by_month[7].mann_kendall.trend == "increasing"
    assert by_month[1].mann_kendall.trend == "no trend"
