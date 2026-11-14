import numpy as np
import pymannkendall as pmk
import pytest

from src.stats.mann_kendall import (
    InsufficientDataError,
    mann_kendall_s,
    mann_kendall_test,
    mann_kendall_variance,
)

# The 6-year example worked out by hand in docs/statistica.md.
HAND_EXAMPLE = np.array([15.0, 15.4, 15.1, 15.6, 15.5, 16.0])


def test_s_hand_example():
    assert mann_kendall_s(HAND_EXAMPLE) == 11


def test_s_is_maximum_for_strictly_increasing_series():
    n = 12
    assert mann_kendall_s(np.arange(n)) == n * (n - 1) // 2


def test_s_is_minimum_for_strictly_decreasing_series():
    n = 12
    assert mann_kendall_s(np.arange(n)[::-1]) == -n * (n - 1) // 2


def test_variance_tie_correction_lowers_variance():
    no_ties = np.arange(10.0)
    with_ties = np.array([1, 1, 1, 2, 3, 4, 5, 6, 7, 8], dtype=float)
    assert mann_kendall_variance(with_ties) < mann_kendall_variance(no_ties)


def test_too_short_series_raises():
    with pytest.raises(InsufficientDataError):
        mann_kendall_test(HAND_EXAMPLE)


def test_missing_values_are_dropped_and_counted():
    values = np.arange(20.0)
    values[[3, 7, 11]] = np.nan
    result = mann_kendall_test(values)
    assert result.n == 17
    assert result.n_missing == 3
    assert result.trend == "increasing"


def test_too_short_after_dropping_missing_raises():
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, np.nan, np.nan, np.nan])
    with pytest.raises(InsufficientDataError):
        mann_kendall_test(values)


def test_constant_series_has_no_trend():
    result = mann_kendall_test(np.full(15, 3.0))
    assert result.s == 0
    assert result.trend == "no trend"
    assert result.p_value == pytest.approx(1.0)


def test_clear_trends_are_detected():
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 0.5, 40)
    assert mann_kendall_test(0.1 * np.arange(40) + noise).trend == "increasing"
    assert mann_kendall_test(-0.1 * np.arange(40) + noise).trend == "decreasing"


def test_false_positive_rate_on_pure_noise():
    # With no trend and alpha = 0.05, about 5% of series should come out "significant".
    rng = np.random.default_rng(42)
    n_series = 400
    false_positives = sum(
        mann_kendall_test(rng.normal(0, 1, 44)).significant for _ in range(n_series)
    )
    assert false_positives / n_series < 0.10


@pytest.mark.parametrize("seed", [1, 2, 3])
@pytest.mark.parametrize("slope", [0.0, 0.02, -0.05])
def test_matches_pymannkendall(seed, slope):
    rng = np.random.default_rng(seed)
    # Rounded to 1 decimal on purpose, so that the series contains ties.
    values = np.round(slope * np.arange(44) + rng.normal(0, 1, 44), 1)
    ours = mann_kendall_test(values)
    ref = pmk.original_test(values)
    assert ours.s == ref.s
    assert ours.var_s == pytest.approx(ref.var_s)
    assert ours.z == pytest.approx(ref.z)
    assert ours.p_value == pytest.approx(ref.p)
    assert ours.tau == pytest.approx(ref.Tau)
