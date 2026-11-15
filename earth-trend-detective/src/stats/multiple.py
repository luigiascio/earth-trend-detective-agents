"""Correction for multiple tests (pure functions)."""

import numpy as np


def benjamini_hochberg(p_values) -> np.ndarray:
    """Benjamini-Hochberg adjusted p-values (q-values), in the same order as the input.

    Controls the false discovery rate: among the tests called significant at q < alpha,
    the expected share of false positives is at most alpha.

    Steps: sort the m p-values; multiply the k-th smallest by m / k; going from the largest
    down, take the running minimum (so q-values never decrease with p); cap at 1.
    """
    p = np.asarray(p_values, dtype=float)
    if p.ndim != 1:
        raise ValueError("p_values must be one-dimensional")
    if np.any((p < 0) | (p > 1) | np.isnan(p)):
        raise ValueError("p_values must be between 0 and 1")
    m = p.size
    if m == 0:
        return p.copy()

    order = np.argsort(p)
    ranked = p[order] * m / np.arange(1, m + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    q = np.empty(m)
    q[order] = np.minimum(ranked, 1.0)
    return q
