"""Seasonal Mann-Kendall test (Hirsch et al., 1982) and seasonal Sen slope.

Each month is compared only with the same month of other years, so the
annual cycle (January vs July) cannot hide or fake a long-term trend.
"""

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

from src.stats.mann_kendall import (
    MIN_OBSERVATIONS,
    InsufficientDataError,
    MannKendallResult,
    mann_kendall_s,
    mann_kendall_test,
    mann_kendall_variance,
)
from src.stats.theil_sen import TheilSenResult, pairwise_slopes, theil_sen


@dataclass(frozen=True)
class SeasonalMannKendallResult:
    trend: str  # "increasing", "decreasing" or "no trend"
    significant: bool
    p_value: float
    z: float
    s: int  # sum of the 12 monthly S values
    var_s: float  # sum of the 12 monthly variances
    tau: float  # S divided by the total number of same-month pairs
    n: int  # observations actually used
    n_missing: int  # NaN values dropped before the test
    alpha: float


@dataclass(frozen=True)
class SeasonalSenResult:
    slope: float  # value units per year
    lower: float
    upper: float
    confidence: float
    n: int
    n_missing: int


@dataclass(frozen=True)
class MonthlyTrend:
    month: int  # 1 = January ... 12 = December
    mann_kendall: MannKendallResult
    sen: TheilSenResult


def _clean_and_split(years, months, values):
    """Drop NaN, then return {month: (years, values)} sorted by year, plus counts."""
    y = np.asarray(years, dtype=float)
    m = np.asarray(months, dtype=int)
    x = np.asarray(values, dtype=float)
    if not (len(y) == len(m) == len(x)):
        raise ValueError("years, months and values must have the same length")

    missing = np.isnan(x)
    y, m, x = y[~missing], m[~missing], x[~missing]
    if len(np.unique(y)) < MIN_OBSERVATIONS:
        raise InsufficientDataError(
            f"{len(np.unique(y))} years with data, at least {MIN_OBSERVATIONS} are needed"
        )

    by_month = {}
    for month in np.unique(m):
        mask = m == month
        order = np.argsort(y[mask])  # Mann-Kendall needs chronological order
        by_month[int(month)] = (y[mask][order], x[mask][order])
    return by_month, len(x), int(missing.sum())


def seasonal_mann_kendall(years, months, values, alpha: float = 0.05) -> SeasonalMannKendallResult:
    """Two-sided seasonal Mann-Kendall test on a monthly series.

    S and its variance are computed within each month and then summed.
    """
    by_month, n, n_missing = _clean_and_split(years, months, values)

    s, var_s, n_pairs = 0, 0.0, 0
    for _, month_values in by_month.values():
        if len(month_values) < 2:
            continue  # a single value has no pair to compare
        s += mann_kendall_s(month_values)
        var_s += mann_kendall_variance(month_values)
        n_pairs += len(month_values) * (len(month_values) - 1) // 2

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

    return SeasonalMannKendallResult(
        trend=trend,
        significant=significant,
        p_value=p_value,
        z=float(z),
        s=s,
        var_s=var_s,
        tau=s / n_pairs,
        n=n,
        n_missing=n_missing,
        alpha=alpha,
    )


def seasonal_sen_slope(years, months, values, confidence: float = 0.95) -> SeasonalSenResult:
    """Median of all same-month pairwise slopes (per year), with a confidence interval.

    The interval uses the same rank method as theil_sen, with the seasonal
    variance of S (sum of the monthly variances).
    """
    by_month, n, n_missing = _clean_and_split(years, months, values)

    slopes, var_s = [], 0.0
    for month_years, month_values in by_month.values():
        if len(month_values) < 2:
            continue
        slopes.append(pairwise_slopes(month_years, month_values))
        var_s += mann_kendall_variance(month_values)

    slopes = np.sort(np.concatenate(slopes))
    n_slopes = len(slopes)
    c = norm.ppf(1 - (1 - confidence) / 2) * np.sqrt(var_s)
    lower_idx = max(int(np.round((n_slopes - c) / 2)) - 1, 0)
    upper_idx = min(int(np.round((n_slopes + c) / 2)), n_slopes - 1)

    return SeasonalSenResult(
        slope=float(np.median(slopes)),
        lower=float(slopes[lower_idx]),
        upper=float(slopes[upper_idx]),
        confidence=confidence,
        n=n,
        n_missing=n_missing,
    )


def trends_by_month(
    years, months, values, alpha: float = 0.05, confidence: float = 0.95
) -> list[MonthlyTrend]:
    """Mann-Kendall and Theil-Sen on each month separately (e.g. the 44 Julys).

    Months with too few values are skipped. These are 12 separate tests: before
    claiming that one month changes, correct for multiple testing (see statistica.md).
    """
    by_month, _, _ = _clean_and_split(years, months, values)

    results = []
    for month, (month_years, month_values) in by_month.items():
        try:
            results.append(
                MonthlyTrend(
                    month=month,
                    mann_kendall=mann_kendall_test(month_values, alpha=alpha),
                    sen=theil_sen(month_years, month_values, confidence=confidence),
                )
            )
        except InsufficientDataError:
            continue
    return results
