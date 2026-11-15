"""Tests for the Benjamini-Hochberg correction."""

import numpy as np
import pytest
from scipy.stats import false_discovery_control

from src.stats.multiple import benjamini_hochberg


def test_hand_worked_example():
    # m = 4. Sorted: 0.01*4/1 = 0.04, 0.02*4/2 = 0.04, 0.03*4/3 = 0.04, 0.5*4/4 = 0.5
    q = benjamini_hochberg([0.03, 0.5, 0.01, 0.02])
    assert q == pytest.approx([0.04, 0.5, 0.04, 0.04])


def test_running_minimum_keeps_order():
    # 0.04*3/2 = 0.06 but the next one gives 0.045*3/3 = 0.045: q is the smaller one
    q = benjamini_hochberg([0.001, 0.04, 0.045])
    assert q == pytest.approx([0.003, 0.045, 0.045])


def test_matches_scipy():
    rng = np.random.default_rng(0)
    p = rng.uniform(0, 1, 40) ** 3
    assert benjamini_hochberg(p) == pytest.approx(false_discovery_control(p, method="bh"))


def test_capped_at_one_and_never_below_p():
    p = np.array([0.9, 0.95, 0.99, 0.2])
    q = benjamini_hochberg(p)
    assert np.all(q <= 1) and np.all(q >= p)


def test_single_test_is_unchanged():
    assert benjamini_hochberg([0.03]) == pytest.approx([0.03])


@pytest.mark.parametrize("bad", [[-0.1, 0.5], [0.2, 1.5], [np.nan]])
def test_invalid_p_values(bad):
    with pytest.raises(ValueError):
        benjamini_hochberg(bad)
