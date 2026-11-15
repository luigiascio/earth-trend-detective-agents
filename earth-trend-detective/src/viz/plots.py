"""Static trend charts (matplotlib). The numbers come from src/stats, never computed here."""

import matplotlib

matplotlib.use("Agg")  # no window: render to file or to the web app

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

# Reference palette (light mode), see the dataviz guidelines.
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e6e5e1"
SERIES_1 = "#2a78d6"
BAND = "#2a78d6"


def plot_trend(
    years: np.ndarray,
    values: np.ndarray,
    slope: float,
    lower: float,
    upper: float,
    title: str,
    unit: str,
    source: str,
) -> Figure:
    """Annual values with the trend line and its confidence band.

    The trend line passes through (median year, median value), the same pivot
    used by the Theil-Sen intercept. slope/lower/upper are per year.
    """
    years = np.asarray(years, dtype=float)
    values = np.asarray(values, dtype=float)
    pivot_t, pivot_x = np.median(years), np.nanmedian(values)
    t = np.array([years.min(), years.max()])

    def line(s: float) -> np.ndarray:
        return pivot_x + s * (t - pivot_t)

    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    # Confidence band: all lines with a slope between lower and upper.
    ax.fill_between(t, line(lower), line(upper), color=BAND, alpha=0.12, linewidth=0)
    ax.plot(years, values, color=SERIES_1, linewidth=2, marker="o", markersize=4, zorder=3)
    ax.plot(t, line(slope), color=TEXT_PRIMARY, linewidth=2, linestyle="--", zorder=4)

    # Direct labels instead of a legend box.
    ax.annotate(
        f"trend {slope * 10:+.3f} {unit}/decade\n95% CI [{lower * 10:.3f}, {upper * 10:.3f}]",
        xy=(t[1], line(slope)[1]),
        xytext=(8, 0),
        textcoords="offset points",
        va="center",
        fontsize=9,
        color=TEXT_PRIMARY,
    )

    ax.set_title(title, loc="left", fontsize=12, color=TEXT_PRIMARY, pad=12)
    ax.set_ylabel(unit, color=TEXT_SECONDARY, fontsize=9)
    ax.tick_params(colors=TEXT_SECONDARY, labelsize=9, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.set_xlim(years.min() - 0.5, years.max() + 0.5)

    fig.text(0.01, 0.01, f"Source: {source}", fontsize=8, color=TEXT_SECONDARY)
    fig.tight_layout(rect=(0, 0.03, 0.82, 1))
    return fig
