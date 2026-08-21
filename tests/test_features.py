"""Tests for ezplot 1.6 — new features + bug-fix regression suite.

Run: python -m pytest tests/  OR  python tests/test_features.py
"""

from __future__ import annotations

import datetime
import math
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

import ezplot as ez
from ezplot import utils


# --------------------------------------------------------------------------- #
# smarter positional syntax
# --------------------------------------------------------------------------- #

def test_line_multi_positional_shared_index():
    # documented: ez.line(y1, y2, y3) → 3 series sharing an index x
    p = ez.line([5, 6, 7], [10, 11, 12], [20, 19, 18])
    assert len(p._series) == 3
    assert p._series[0]["x"] == [0.0, 1.0, 2.0]
    svg = p.svg()
    assert "y1" in svg and "y2" in svg and "y3" in svg


def test_line_positional_first_is_index_x():
    # ez.line(x, y1, y2) with an index-looking first arg → x + 2 series
    p = ez.line([0, 1, 2], [10, 11, 12], [20, 19, 18])
    assert len(p._series) == 2
    assert p._series[0]["x"] == [0.0, 1.0, 2.0]
    assert p._series[0]["y"] == [10.0, 11.0, 12.0]


def test_line_positional_even_grid_first_is_x():
    p = ez.line([0, 2, 4, 6], [1, 2, 3, 4], [4, 3, 2, 1])
    assert len(p._series) == 2
    assert p._series[0]["x"] == [0.0, 2.0, 4.0, 6.0]


def test_scatter_multi_positional():
    p = ez.scatter([1, 2, 3], [4, 5, 6], [7, 8, 9])
    assert len(p._series) == 3
    assert p._series[0]["x"] == [0.0, 1.0, 2.0]
    assert "<circle" in p.svg()


def test_bar_multi_positional():
    p = ez.bar(["A", "B"], [1, 2], [3, 4], labels=["x", "y"])
    assert len(p._series) == 2
    svg = p.svg()
    assert "x" in svg and "y" in svg


def test_plot_alias_multi():
    assert len(ez.plot([1, 2], [3, 4], [5, 6])._series) == 3


# --------------------------------------------------------------------------- #
# bug fixes
# --------------------------------------------------------------------------- #

def test_bar_none_categories_keeps_data():
    # regression: ez.bar(None, [1, 2, 3]) used to drop all values
    p = ez.bar(None, [1, 2, 3])
    assert p._series[0]["values"] == [1.0, 2.0, 3.0]
    assert "<rect" in p.svg()


def test_bar_dict_with_values_toggle():
    p = ez.bar({"A": 10, "B": 25}, values=True)
    assert p._show_values is True
    assert p._series[0]["values"] == [10.0, 25.0]
    assert "10" in p.svg()


def test_barh_values_toggle_keyword():
    p = ez.barh(["A", "B"], [3, 7], values=True)
    assert p._horizontal is True
    assert p._show_values is True
    svg = p.svg()
    assert "7" in svg


def test_colors_on_single_series_bar():
    # regression: .colors() was ignored for single-series bars
    svg = ez.bar(["A", "B"], [1, 2]).colors("#ff0000").svg()
    assert "#ff0000" in svg


def test_logy_actually_renders():
    svg = ez.line([1, 2, 3], [1, 10, 100]).logy().svg()
    labels = re.findall(r">([\d.k\-]+)</text>", svg)
    assert "10" in labels and "100" in labels
    assert len(ez.line([1, 2, 3], [1, 10, 100]).logy().png_bytes()) > 100


def test_logx_and_loglog():
    svg = ez.line([1, 10, 100], [1, 2, 3]).logx().svg()
    labels = re.findall(r">([\d.k\-]+)</text>", svg)
    assert "10" in labels and "100" in labels
    assert "<svg" in ez.line([1, 10, 100], [1, 10, 100]).logx().logy().svg()


def test_log_scale_falls_back_on_nonpositive():
    # non-positive values disable the log scale instead of crashing
    svg = ez.line([1, 2, 3], [0, 10, 100]).logy().svg()
    assert "<svg" in svg


def test_log_ticks_util():
    assert utils.log_ticks(1, 100) == [1.0, 10.0, 100.0]
    assert utils.log_ticks(2, 500) == [10.0, 100.0]
    assert len(utils.log_ticks(0.5, 2000)) >= 3


def test_hbar_no_numeric_category_labels():
    # regression: horizontal bars showed meaningless 0..1 labels
    svg = ez.bar(["A", "B", "C"], [3, 7, 2]).horizontal().svg()
    labels = re.findall(r">([\d.k\-]+)</text>", svg)
    assert "0.2" not in labels and "0.4" not in labels
    assert "A" in svg and "B" in svg and "C" in svg


def test_hbar_value_labels():
    svg = ez.bar(["A", "B"], [3, 7]).horizontal().values().svg()
    assert "3" in svg and "7" in svg


def test_stacked_bar_svg_and_raster():
    p = ez.bar(["A", "B"], [[1, 2], [3, 1]], labels=["x", "y"]).stacked()
    assert "<rect" in p.svg()
    assert len(p.png_bytes()) > 100


def test_stacked_bar_mixed_signs_split_around_zero():
    svg = (
        ez.bar(["Net"], [[3], [-2]], labels=["up", "down"])
        .stacked()
        .legend(False)
        .grid(False)
        .ylim(-4, 4)
        .svg()
    )
    rects = re.findall(
        r'<rect x="[\d.]+" y="([\d.]+)" width="[\d.]+" height="([\d.]+)" rx="2" fill="#[0-9a-fA-F]{6}" clip-path=',
        svg,
    )
    assert len(rects) == 2
    pos_y = float(rects[0][0])
    neg_y = float(rects[1][0])
    assert pos_y < 150
    assert neg_y > 180
    assert len(
        ez.bar(["Net"], [[3], [-2]], labels=["up", "down"]).stacked().ylim(-4, 4).png_bytes()
    ) > 100


def test_dashed_lines_reach_raster():
    # regression: dashed lines rendered solid in PNG
    b = ez.line([1, 2, 3], [1, 2, 1]).dashed().png_bytes()
    assert len(b) > 100


def test_xlim_datetime_coercion():
    # regression: .xlim() with datetimes was silently ignored
    a = datetime.datetime(2026, 1, 1)
    b = datetime.datetime(2026, 2, 1)
    p = ez.line([1, 2, 3], [1, 2, 3]).xlim(a, b)
    assert p._xlim is not None
    assert abs(p._xlim[0] - a.timestamp()) < 1.0


def test_annotate_hline_vline_datetime():
    d = datetime.datetime(2026, 6, 1)
    svg = ez.line([1, 2, 3], [1, 2, 3]).vline(d).svg()
    assert "<svg" in svg
    svg = ez.line([1, 2, 3], [1, 2, 3]).annotate(d, 2, "d").svg()
    assert "d" in svg
    svg = ez.line([1, 2, 3], [1, 2, 3]).hline(d).axvspan(d, d).svg()
    assert "<svg" in svg


def test_xticks_datetime():
    d1 = datetime.datetime(2026, 1, 1)
    d2 = datetime.datetime(2026, 2, 1)
    p = ez.line([1, 2, 3], [1, 2, 3]).xticks([d1, d2])
    assert len(p._xticks) == 2
    assert "<svg" in p.svg()


def test_area_nan_gaps_segmented():
    svg = ez.area([1, 2, 3, 4], [1, math.nan, 3, 4]).svg()
    assert "<path" in svg


def test_heatmap_svg_labels_not_clipped():
    svg = ez.heatmap(
        [[1, 2], [3, 4]],
        row_labels=["alpha", "beta"],
        col_labels=["left", "right"],
        show_values=False,
    ).svg()
    alpha = re.search(r'(<text[^>]*>alpha</text>)', svg)
    right = re.search(r'(<text[^>]*>right</text>)', svg)
    assert alpha and "clip-path" not in alpha.group(1)
    assert right and "clip-path" not in right.group(1)


def test_annotate_anchor_end():
    svg = ez.line([1, 2, 3], [1, 2, 3]).annotate(2, 2, "note", anchor="end").svg()
    assert "note" in svg


def test_hbar_hline_maps_to_value_axis():
    p = ez.bar(["A", "B"], [3, 7]).horizontal().hline(5)
    assert "<svg" in p.svg()
    assert len(p.png_bytes()) > 100


# --------------------------------------------------------------------------- #
# new chart kinds
# --------------------------------------------------------------------------- #

def test_step_chart():
    svg = ez.step([0, 1, 2, 3], [0, 2, 1, 3], t="Steps").svg()
    assert "<path" in svg
    assert "Steps" in svg
    # step segments produce L nx,{same-y} L nx,{new-y} pairs
    assert svg.count(" L ") >= 4
    assert len(ez.step([0, 1, 2], [1, 0, 1]).png_bytes()) > 100


def test_step_method_on_line():
    p = ez.line([0, 1, 2], [1, 0, 1]).step()
    assert p._step is True
    assert "<path" in p.svg()


def test_boxplot_basic():
    svg = ez.boxplot([1, 2, 3, 4, 5, 20], t="Box").svg()
    assert "<rect" in svg
    assert "Box" in svg
    assert len(ez.boxplot([1, 2, 3, 4, 5, 20]).png_bytes()) > 100


def test_boxplot_multi_and_outliers():
    data = [[1, 2, 3], [2, 4, 8, 30], [5, 6, 7]]
    svg = ez.boxplot(data, labels=["a", "b", "c"]).svg()
    assert "a" in svg and "b" in svg and "c" in svg
    # outlier circles (fill="none" stroke)
    assert 'fill="none"' in svg


def test_boxplot_dict_and_horizontal():
    svg = ez.boxplot({"A": [1, 2, 3], "B": [2, 4, 8]}).svg()
    assert "A" in svg
    svg = ez.boxplot({"A": [1, 2, 3]}).horizontal().svg()
    assert "<rect" in svg


def test_box_stats_util():
    s = utils.box_stats([1, 2, 3, 4, 5, 100])
    assert abs(s["q1"] - 2.25) < 1e-9
    assert abs(s["med"] - 3.5) < 1e-9
    assert abs(s["q3"] - 4.75) < 1e-9
    assert 100.0 in s["outliers"]
    assert s["lo"] == 1.0 and s["hi"] == 5.0
    s2 = utils.box_stats([])
    assert s2["q1"] == 0.0


def test_heatmap_basic():
    m = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    svg = ez.heatmap(m, t="Heat").svg()
    assert svg.count("<rect") >= 9
    assert "Heat" in svg
    assert len(ez.heatmap(m).png_bytes()) > 100


def test_heatmap_labels_and_nan():
    m = [[1, None, 3], [4, 5, 6], [7, 8, 9]]
    svg = ez.heatmap(
        m,
        row_labels=["a", "b", "c"],
        col_labels=["x", "y", "z"],
        show_values=False,
    ).svg()
    assert "a" in svg and "x" in svg
    assert "<rect" in svg


def test_heatmap_no_colorbar():
    svg = ez.heatmap([[1, 2, 3], [4, 5, 6], [7, 8, 9]], colorbar=False).svg()
    assert "<svg" in svg


def test_heatmap_colorbar_labels():
    svg = ez.heatmap([[1, 2], [3, 4], [5, 6]]).svg()
    assert "5" in svg and "1" in svg  # colorbar min/max


def test_function_factory():
    p = ez.function(lambda x: x * x, -5, 5)
    assert "<path" in p.svg()
    assert p._markers is False
    assert len(p.png_bytes()) > 100


def test_fn_alias():
    assert "<path" in ez.fn(lambda x: x, 0, 1, steps=10).svg()


def test_heatmap_empty_data():
    assert "No data" in ez.heatmap([]).svg()


def test_boxplot_empty_data():
    svg = ez.boxplot([]).svg()
    assert "<svg" in svg


# --------------------------------------------------------------------------- #
# plot methods: trend / smooth / errors / rotation / sort
# --------------------------------------------------------------------------- #

def test_trend_line():
    svg = ez.scatter([1, 2, 3, 4], [2, 4, 6, 9]).trend().svg()
    assert "trend" in svg
    assert svg.count("<path") >= 1
    assert len(ez.line([1, 2, 3], [2, 4, 7]).trend().png_bytes()) > 100


def test_trendline_alias_and_color():
    svg = ez.line([1, 2, 3], [2, 4, 7]).trendline(color="#00ff00").svg()
    assert "#00ff00" in svg


def test_trend_degenerate_data():
    # constant y → no trend line, but must render
    assert "<svg" in ez.line([1, 2, 3], [5, 5, 5]).trend().svg()


def test_linear_regression_util():
    fit = utils.linear_regression([1, 2, 3], [2, 4, 6])
    assert fit is not None
    slope, intercept, r2 = fit
    assert abs(slope - 2.0) < 1e-9
    assert abs(intercept) < 1e-9
    assert r2 > 0.999
    assert utils.linear_regression([1], [2]) is None


def test_smooth():
    p = ez.line([1, 5, 1, 5, 1]).smooth(3)
    svg = p.svg()
    assert "<path" in svg
    prep = p._prepare_xy()
    smoothed = prep[0][0]["y"]
    assert abs(smoothed[1] - (1 + 5 + 1) / 3) < 1e-9


def test_smooth_off():
    p = ez.line([1, 5, 1]).smooth(3).smooth(None)
    assert p._smooth is None


def test_yerr_xerr():
    svg = ez.line([1, 2, 3], [2, 4, 3]).yerr(0.5).xerr(0.2).svg()
    assert "<svg" in svg
    p = ez.line([1, 2, 3], [2, 4, 3]).yerr([0.5, 0.2, 0.4])
    assert len(p.png_bytes()) > 100


def test_yerr_nested_per_series():
    p = ez.line([1, 2], [[1, 2], [2, 3]], labels=["a", "b"]).yerr([[0.5, 0.5], [0.2, 0.2]])
    assert "<svg" in p.svg()


def test_xrot():
    svg = ez.line([1, 2, 3], [1, 2, 3]).xrot(45).svg()
    assert "rotate(-45" in svg
    svg2 = ez.line([1, 2, 3], [1, 2, 3]).xrot().svg()
    assert "rotate(-35" in svg2
    assert len(ez.line([1, 2, 3], [1, 2, 3]).xrot(45).png_bytes()) > 100


def test_xticks_style_kwarg():
    svg = ez.line([1, 2, 3], [1, 2, 3], xticks=[0, 1, 2]).svg()
    assert "0" in svg


def test_bar_sort_by_value():
    p = ez.bar(["A", "B", "C"], [2, 9, 4]).sort()
    svg = p.svg()
    pos = {}
    for m in re.finditer(
        r'<text x="([\d.]+)" y="[\d.]+" text-anchor="middle"[^>]*>([ABC])</text>', svg
    ):
        pos[m.group(2)] = float(m.group(1))
    assert pos["B"] < pos["C"] < pos["A"]  # 9 first, then 4, then 2


def test_values_custom_fmt():
    svg = ez.bar(["A", "B"], [1.5, 2.25]).values("{:.1f}").svg()
    assert "1.5" in svg and "2.2" in svg


# --------------------------------------------------------------------------- #
# factories & aliases
# --------------------------------------------------------------------------- #

def test_barh_factory():
    p = ez.barh(["A", "B"], [3, 7])
    assert p._horizontal is True
    assert "<rect" in p.svg()


def test_donut_factory():
    p = ez.donut({"A": 30, "B": 70})
    assert p._donut is True
    assert "<path" in p.svg()


def test_chart_alias():
    assert ez.chart({"A": 1, "B": 2}).kind == "bar"
    assert ez.chart([1, 2, 3]).kind == "line"
    assert ez.chart([(1, 2), (3, 4), (2, 1)]).kind == "scatter"


def test_box_alias():
    assert "<rect" in ez.box([1, 2, 3]).svg()


def test_auto_heatmap():
    m = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    assert ez.auto(m).kind == "heat"
    # small 2-row matrix stays a grouped bar
    assert ez.auto([[1, 2, 3], [4, 5, 6]]).kind == "bar"


def test_heatmap_cmap_options():
    for cmap in ("blues", "reds", "viridis"):
        svg = ez.heatmap([[1, 2, 3], [4, 5, 6], [7, 8, 9]], cmap=cmap).svg()
        assert "<rect" in svg
    from ezplot.style import get_heatmap
    assert get_heatmap("nope") == get_heatmap("blues")


def test_interp_color_util():
    assert utils.interp_color("#000000", "#ffffff", 0.5) == "#808080"
    assert utils.interp_color("#000000", "#ffffff", 0.0) == "#000000"
    assert utils.interp_color("#000000", "#ffffff", 1.0) == "#ffffff"


# --------------------------------------------------------------------------- #
# smart data inputs
# --------------------------------------------------------------------------- #

def test_numpy_2d_series():
    np = pytest.importorskip("numpy")
    p = ez.line(np.array([[1, 2, 3], [3, 2, 1]]))
    assert len(p._series) == 2
    assert "<path" in p.svg()


def test_numpy_heatmap():
    np = pytest.importorskip("numpy")
    m = np.arange(12).reshape(3, 4)
    assert ez.auto(m).kind == "heat"


def test_dataframe_like_labels():
    class FakeDF:
        columns = ["alpha", "beta"]

        def __getitem__(self, key):
            return {"alpha": [1, 2, 3], "beta": [3, 2, 1]}[key]

    p = ez.line(FakeDF())
    assert [s["label"] for s in p._series] == ["alpha", "beta"]
    svg = p.svg()
    assert "alpha" in svg and "beta" in svg


def test_looks_like_index_util():
    assert utils.looks_like_index([0, 1, 2, 3])
    assert utils.looks_like_index([0, 2, 4, 6])
    assert not utils.looks_like_index([1, 2, 3])  # ambiguous → treat as series
    assert not utils.looks_like_index([5, 6, 7])
    assert not utils.looks_like_index([2, 1, 0])


def test_box_stats_util_quantiles():
    s = utils.box_stats(list(range(1, 11)))
    assert s["q1"] == 3.25
    assert s["med"] == 5.5
    assert s["q3"] == 7.75


# --------------------------------------------------------------------------- #
# misc intelligence & stability
# --------------------------------------------------------------------------- #

def test_unknown_style_kwarg_warns():
    with pytest.warns(UserWarning):
        ez.line([1, 2, 3], titel="oops")


def test_known_style_kwargs_do_not_warn():
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        p = ez.line([1, 2, 3], t="ok", c="red", theme="dark", xticks=[1, 2])
        assert "<svg" in p.svg()


def test_style_method_new_options():
    p = ez.line([1, 2, 3]).style(xticks=[1, 2], xrot=30, smooth=3, trend=True)
    assert p._xrot == 30.0
    assert "<svg" in p.svg()


def test_auto_still_picks_classic():
    assert ez.auto([1, 2, 3]).kind == "line"
    assert ez.auto({"A": 1, "B": 2}).kind == "bar"
    assert ez.auto([(1, 2), (3, 1), (0, 4)]).kind == "scatter"
    assert ez.auto(["a", "b", "a"]).kind == "bar"


def test_new_kinds_never_raise_raster():
    for p in [
        ez.step([1, 2], [1, 2]),
        ez.boxplot([[1, 2], [3, 4]]),
        ez.heatmap([[1, 2, 3], [4, 5, 6], [7, 8, 9]]),
        ez.fn(lambda x: x, 0, 1),
    ]:
        assert len(p.png_bytes()) > 100


if __name__ == "__main__":
    failed = 0
    for name, fn in list(globals().items()):
        if not (name.startswith("test_") and callable(fn)):
            continue
        try:
            fn()
            print("ok", name)
        except Exception as e:  # noqa: BLE001
            failed += 1
            print("FAIL", name, "→", e)
    if failed:
        print(f"{failed} failed")
        sys.exit(1)
    print("all passed")
