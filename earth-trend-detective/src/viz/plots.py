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


# Dark theme of the web app (night blue). One accent per trend direction, validated with the
# dataviz palette checker on the dark surface (lightness band, colour-blind separation, contrast).
DARK = {
    "surface": "#0f1a2c",
    "text_primary": "#ffffff",
    "text_secondary": "#d3d9e2",
    "grid": "#24314a",
    "series": "#d45d9a",  # observed values: magenta, validated against both trend accents
}
TREND_COLORS = {"increasing": "#d97324", "decreasing": "#3b9bd6", "no trend": "#b4bccb"}


def plot_trend(
    years: np.ndarray,
    values: np.ndarray,
    slope: float,
    lower: float,
    upper: float,
    title: str,
    unit: str,
    source: str,
    trend: str | None = None,
    dark: bool = False,
) -> Figure:
    """Annual values with the trend line and its confidence band.

    The trend line passes through (median year, median value), the same pivot
    used by the Theil-Sen intercept. slope/lower/upper are per year.
    With dark=True the web-app theme is used and the trend is coloured by `trend`
    (orange increasing, light blue decreasing, grey no significant trend).
    """
    surface = DARK["surface"] if dark else SURFACE
    text_primary = DARK["text_primary"] if dark else TEXT_PRIMARY
    text_secondary = DARK["text_secondary"] if dark else TEXT_SECONDARY
    grid = DARK["grid"] if dark else GRID
    series = DARK["series"] if dark else SERIES_1
    accent = TREND_COLORS.get(trend, text_primary) if dark else TEXT_PRIMARY
    band = TREND_COLORS.get(trend, BAND) if dark else BAND

    years = np.asarray(years, dtype=float)
    values = np.asarray(values, dtype=float)
    pivot_t, pivot_x = np.median(years), np.nanmedian(values)
    t = np.array([years.min(), years.max()])

    def line(s: float) -> np.ndarray:
        return pivot_x + s * (t - pivot_t)

    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=150)
    fig.patch.set_facecolor(surface)
    ax.set_facecolor(surface)

    # Confidence band: all lines with a slope between lower and upper.
    ax.fill_between(t, line(lower), line(upper), color=band, alpha=0.28 if dark else 0.12, linewidth=0)
    ax.plot(years, values, color=series, linewidth=2, marker="o", markersize=4, zorder=3)
    ax.plot(t, line(slope), color=accent, linewidth=2.5, linestyle="--", zorder=4)

    # Direct labels instead of a legend box.
    ax.annotate(
        f"trend {slope * 10:+.3f} {unit}/decade\n95% CI [{lower * 10:.3f}, {upper * 10:.3f}]",
        xy=(t[1], line(slope)[1]),
        xytext=(8, 0),
        textcoords="offset points",
        va="center",
        fontsize=9,
        color=text_primary,
    )

    ax.set_title(title, loc="left", fontsize=12, color=text_primary, pad=12)
    ax.set_ylabel(unit, color=text_secondary, fontsize=9)
    ax.tick_params(colors=text_secondary, labelsize=9, length=0)
    ax.grid(axis="y", color=grid, linewidth=0.8)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(grid)
    ax.set_xlim(years.min() - 0.5, years.max() + 0.5)

    fig.text(0.01, 0.01, f"Source: {source}", fontsize=8, color=text_secondary)
    fig.tight_layout(rect=(0, 0.03, 0.82, 1))
    return fig
