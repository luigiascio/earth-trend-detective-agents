"""Theil-Sen slope estimator with Sen's confidence interval."""

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

from src.stats.mann_kendall import (
    MIN_OBSERVATIONS,
    InsufficientDataError,
    mann_kendall_variance,
)


@dataclass(frozen=True)
class TheilSenResult:
    slope: float  # value units per time unit (e.g. degC per year if times are in years)
    lower: float  # lower bound of the confidence interval for the slope
    upper: float  # upper bound
    intercept: float  # so that the trend line is intercept + slope * t
    confidence: float  # e.g. 0.95
    n: int  # observations actually used
    n_missing: int  # NaN values dropped before the estimate


def pairwise_slopes(times: np.ndarray, values: np.ndarray) -> np.ndarray:
    """Return the slope (x_j - x_i) / (t_j - t_i) for every pair i < j."""
    if len(times) != len(values):
        raise ValueError("times and values must have the same length")
    n = len(values)

    slopes = []
    for i in range(n - 1):
        for j in range(i + 1, n):
            slopes.append((values[j] - values[i]) / (times[j] - times[i]))

    return np.array(slopes, dtype=float)


def theil_sen(times: np.ndarray, values: np.ndarray, confidence: float = 0.95) -> TheilSenResult:
    """Median of all pairwise slopes, with Sen's (1968) confidence interval.

    NaN values are dropped (and counted in n_missing), never filled.
    Raises InsufficientDataError if fewer than MIN_OBSERVATIONS values remain.
    """
    t = np.asarray(times, dtype=float)
    x = np.asarray(values, dtype=float)
    missing = np.isnan(x)
    t, x = t[~missing], x[~missing]
    n = len(x)
    if n < MIN_OBSERVATIONS:
        raise InsufficientDataError(
            f"{n} valid observations, at least {MIN_OBSERVATIONS} are needed"
        )

    slopes = np.sort(pairwise_slopes(t, x))
    slope = float(np.median(slopes))
    intercept = float(np.median(x) - slope * np.median(t))

    # Confidence interval: walk C/2 positions away from the median in the sorted
    # slopes, where C depends on the Mann-Kendall variance of S.
    n_slopes = len(slopes)
    c = norm.ppf(1 - (1 - confidence) / 2) * np.sqrt(mann_kendall_variance(x))
    lower_idx = max(int(np.round((n_slopes - c) / 2)) - 1, 0)
    upper_idx = min(int(np.round((n_slopes + c) / 2)), n_slopes - 1)

    return TheilSenResult(
        slope=slope,
        lower=float(slopes[lower_idx]),
        upper=float(slopes[upper_idx]),
        intercept=intercept,
        confidence=confidence,
        n=n,
        n_missing=int(missing.sum()),
    )


if __name__ == "__main__":
    print(pairwise_slopes(np.array([0, 1, 2]), np.array([0, 2, 4])))  # expected: [2. 2. 2.]
