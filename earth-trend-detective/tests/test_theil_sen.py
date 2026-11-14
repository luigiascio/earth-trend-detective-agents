import numpy as np
import pytest
from scipy.stats import linregress, theilslopes

from src.stats.mann_kendall import InsufficientDataError
from src.stats.theil_sen import pairwise_slopes, theil_sen


def test_pairwise_slopes_on_a_straight_line():
    slopes = pairwise_slopes(np.array([0, 1, 2]), np.array([0, 2, 4]))
    assert slopes.tolist() == [2.0, 2.0, 2.0]


def test_pairwise_slopes_count():
    n = 10
    assert len(pairwise_slopes(np.arange(n), np.arange(n))) == n * (n - 1) // 2


def test_pairwise_slopes_rejects_different_lengths():
    with pytest.raises(ValueError):
        pairwise_slopes(np.arange(3), np.arange(4))


def test_hand_example_median_slope():
    # docs/statistica.md: median of the 15 slopes is 0.20 degC/year.
    values = np.array([15.0, 15.4, 15.1, 15.6, 15.5, 16.0])
    assert np.median(pairwise_slopes(np.arange(6), values)) == pytest.approx(0.20)


def test_recovers_known_slope():
    rng = np.random.default_rng(0)
    years = np.arange(1981, 2025, dtype=float)
    true_slope = 0.035  # degC per year
    values = 15 + true_slope * (years - 1981) + rng.normal(0, 0.3, len(years))
    result = theil_sen(years, values)
    assert result.slope == pytest.approx(true_slope, abs=0.01)
    assert result.lower <= true_slope <= result.upper


def test_interval_contains_the_estimate():
    rng = np.random.default_rng(1)
    years = np.arange(40, dtype=float)
    result = theil_sen(years, rng.normal(0, 1, 40))
    assert result.lower <= result.slope <= result.upper


def test_robust_to_one_outlier():
    rng = np.random.default_rng(2)
    years = np.arange(44, dtype=float)
    values = 15 + 0.03 * years + rng.normal(0, 0.2, 44)
    spoiled = values.copy()
    spoiled[-1] = 30.0  # sensor error

    clean = theil_sen(years, values).slope
    theil_sen_shift = abs(theil_sen(years, spoiled).slope - clean)
    ols_shift = abs(linregress(years, spoiled).slope - linregress(years, values).slope)
    assert theil_sen_shift < 0.005
    # Ordinary least squares is dragged away by the same single value, far more.
    assert ols_shift > 10 * theil_sen_shift


def test_missing_values_are_dropped_and_counted():
    years = np.arange(20, dtype=float)
    values = 2.0 * years
    values[[0, 5]] = np.nan
    result = theil_sen(years, values)
    assert result.slope == pytest.approx(2.0)
    assert result.n == 18
    assert result.n_missing == 2


def test_too_short_series_raises():
    with pytest.raises(InsufficientDataError):
        theil_sen(np.arange(5), np.arange(5))


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_matches_scipy(seed):
    rng = np.random.default_rng(seed)
    years = np.arange(1981, 2025, dtype=float)
    values = np.round(0.03 * years + rng.normal(0, 0.5, len(years)), 1)
    ours = theil_sen(years, values)
    ref = theilslopes(values, years, 0.95)
    assert ours.slope == pytest.approx(ref.slope)
    assert ours.intercept == pytest.approx(ref.intercept)
    assert ours.lower == pytest.approx(ref.low_slope)
    assert ours.upper == pytest.approx(ref.high_slope)
