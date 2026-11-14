"""Mann-Kendall trend test (original version, no autocorrelation correction yet)."""

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

# Below this the normal approximation for S is unreliable.
MIN_OBSERVATIONS = 10


class InsufficientDataError(ValueError):
    """Raised when a series is too short to test for a trend."""


@dataclass(frozen=True)
class MannKendallResult:
    trend: str  # "increasing", "decreasing" or "no trend"
    significant: bool
    p_value: float
    z: float
    s: int
    var_s: float
    tau: float  # Kendall's tau: S divided by the number of pairs, between -1 and 1
    n: int  # observations actually used
    n_missing: int  # NaN values dropped before the test
    alpha: float


def mann_kendall_s(values: np.ndarray) -> int:
    """Return the Mann-Kendall S statistic: sum of sign(x_j - x_i) over all pairs i < j."""
    S = 0
    for i in range(len(values) - 1):
        for j in range(i + 1, len(values)):
            S += np.sign(values[j] - values[i])
    return int(S)


def mann_kendall_variance(values: np.ndarray) -> float:
    """Variance of S under the no-trend hypothesis, corrected for tied values."""
    n = len(values)
    _, counts = np.unique(values, return_counts=True)
    ties = counts[counts > 1]  # size of each group of equal values
    tie_term = np.sum(ties * (ties - 1) * (2 * ties + 5))
    return float((n * (n - 1) * (2 * n + 5) - tie_term) / 18)


def mann_kendall_test(values: np.ndarray, alpha: float = 0.05) -> MannKendallResult:
    """Two-sided Mann-Kendall test for a monotonic trend.

    NaN values are dropped (and counted in n_missing), never filled.
    Raises InsufficientDataError if fewer than MIN_OBSERVATIONS values remain.
    """
    x = np.asarray(values, dtype=float)
    missing = np.isnan(x)
    x = x[~missing]
    n = len(x)
    if n < MIN_OBSERVATIONS:
        raise InsufficientDataError(
            f"{n} valid observations, at least {MIN_OBSERVATIONS} are needed"
        )

    s = mann_kendall_s(x)
    var_s = mann_kendall_variance(x)

    # Continuity correction: S only takes integer values.
    if s > 0 and var_s > 0:
        z = (s - 1) / np.sqrt(var_s)
    elif s < 0 and var_s > 0:
        z = (s + 1) / np.sqrt(var_s)
    else:
        z = 0.0

    p_value = float(2 * norm.sf(abs(z)))  # sf = 1 - cdf, without rounding to 0
    significant = p_value < alpha
    if not significant:
        trend = "no trend"
    elif z > 0:
        trend = "increasing"
    else:
        trend = "decreasing"

    return MannKendallResult(
        trend=trend,
        significant=significant,
        p_value=p_value,
        z=float(z),
        s=s,
        var_s=var_s,
        tau=s / (n * (n - 1) / 2),
        n=n,
        n_missing=int(missing.sum()),
        alpha=alpha,
    )


if __name__ == "__main__":
    print(mann_kendall_s(np.array([3, 5, 4, 7])))  # expected: 4
