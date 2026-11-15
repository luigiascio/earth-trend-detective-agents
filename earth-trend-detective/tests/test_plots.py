import numpy as np

from src.viz.plots import plot_trend


def test_plot_trend_returns_a_figure_with_series_and_trend(tmp_path):
    years = np.arange(1981, 2025)
    values = 15 + 0.03 * (years - 1981)
    fig = plot_trend(years, values, 0.03, 0.02, 0.04, "Test", "degC", "NASA POWER (MERRA2)")
    ax = fig.axes[0]
    assert len(ax.lines) == 2  # annual series + trend line
    assert "+0.300 degC/decade" in ax.texts[0].get_text()
    out = tmp_path / "chart.png"
    fig.savefig(out)
    assert out.stat().st_size > 0
