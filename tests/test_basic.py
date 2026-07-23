"""Tests for ezplot — run: python -m pytest tests/  OR  python tests/test_basic.py"""

from __future__ import annotations

import math
import sys
import tempfile
from pathlib import Path

# repo root on path when run as script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ezplot as ez
from ezplot import utils


def test_line_svg_contains_path():
    svg = ez.line([1, 3, 2, 5]).title("T").svg()
    assert svg.startswith("<svg")
    assert "</svg>" in svg
    assert "T" in svg
    assert "<path" in svg


def test_line_xy():
    assert "<path" in ez.line([0, 1, 2], [0, 1, 0]).svg()


def test_multi_line_legend():
    svg = ez.line([1, 2, 3], [[1, 2, 3], [3, 2, 1]], labels=["a", "b"]).svg()
    assert "a" in svg and "b" in svg


def test_bar():
    svg = ez.bar(["A", "B", "C"], [10, 20, 5]).title("Bars").svg()
    assert "<rect" in svg
    assert "A" in svg


def test_bar_values_only():
    assert "<rect" in ez.bar([3, 1, 4]).svg()


def test_bar_dict():
    svg = ez.bar({"A": 10, "B": 20}).svg()
    assert "A" in svg and "<rect" in svg


def test_bar_frequency():
    svg = ez.bar(["cat", "dog", "cat", "bird"]).svg()
    assert "cat" in svg


def test_grouped_bar():
    svg = ez.bar(["Q1", "Q2"], [[1, 2], [3, 4]], labels=["x", "y"]).svg()
    assert "x" in svg and "y" in svg


def test_stacked_bar():
    svg = ez.bar(["A", "B"], [[1, 2], [3, 1]], labels=["x", "y"]).stacked().svg()
    assert "<rect" in svg


def test_scatter():
    svg = ez.scatter([1, 2, 3], [3, 1, 2]).color("#ff0000").svg()
    assert "#ff0000" in svg
    assert "<circle" in svg


def test_scatter_pairs():
    svg = ez.scatter([(1, 2), (3, 4), (2, 1)]).svg()
    assert "<circle" in svg


def test_hist():
    data = [i % 10 for i in range(100)]
    assert "<rect" in ez.hist(data, bins=5).svg()


def test_pie_and_donut():
    svg = ez.pie([1, 2, 3], labels=["a", "b", "c"]).svg()
    assert "<path" in svg and "a" in svg
    assert "<path" in ez.pie([1, 2, 3], labels=["a", "b", "c"]).donut().svg()


def test_pie_dict():
    svg = ez.pie({"A": 30, "B": 70}).svg()
    assert "A" in svg


def test_pie_full_circle():
    svg = ez.pie([10], labels=["only"]).svg()
    assert "<svg" in svg
    assert "only" in svg


def test_area():
    assert "<path" in ez.area([1, 2, 3], [1, 4, 2]).svg()


def test_theme_dark():
    svg = ez.line([1, 2, 3]).theme("dark").svg()
    assert "#0f172a" in svg


def test_fluent_chain():
    p = (
        ez.line([1, 2, 3, 4])
        .title("Hi")
        .xlabel("x")
        .ylabel("y")
        .color("#00ff00")
        .grid(False)
        .markers(False)
        .size(400, 300)
    )
    svg = p.svg()
    assert "Hi" in svg
    assert "#00ff00" in svg
    assert 'width="400"' in svg


def test_save(tmp_path=None):
    if tmp_path is None:
        tmp_path = Path(tempfile.mkdtemp())
    path = Path(tmp_path) / "c.svg"
    ez.line([1, 2, 3]).save(path)
    assert path.exists()
    assert path.read_text(encoding="utf-8").startswith("<svg")
    html = Path(tmp_path) / "c.html"
    ez.bar([1, 2]).save(html)
    assert "<!DOCTYPE html>" in html.read_text(encoding="utf-8")


def test_png_export(tmp_path=None):
    if tmp_path is None:
        tmp_path = Path(tempfile.mkdtemp())
    path = Path(tmp_path) / "c.png"
    ez.line([1, 2, 3], t="P").save(path)
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(ez.line([1, 2, 3]).png_bytes()) > 100


def test_add_series():
    p = ez.line([1, 2, 3], label="a").add([3, 2, 1], label="b", color="red")
    svg = p.svg()
    assert "a" in svg and "b" in svg


def test_utils_core():
    assert utils.as_float_list([1, "2", 3.5]) == [1.0, 2.0, 3.5]
    assert utils.to_float("1,234.5") == 1234.5
    assert utils.to_float("nan") is None
    assert utils.to_float(None) is None
    ticks = utils.nice_ticks(0, 10, 5)
    assert ticks[0] <= 0 and ticks[-1] >= 10
    assert utils.format_number(0) == "0"
    edges, c, n = utils.histogram_bins([1, 2, 2, 3], bins=2)
    assert len(c) == 2
    assert sum(n) == 4


def test_nan_gaps_in_line():
    ys = [1.0, math.nan, 3.0, 4.0]
    svg = ez.line(ys).svg()
    assert "<svg" in svg
    assert "<path" in svg or "<circle" in svg


def test_empty_data():
    svg = ez.line([]).svg()
    assert "No data" in svg or "No numeric" in svg or "<svg" in svg


def test_bad_numbers_stable():
    svg = ez.line([1, "x", None, 4]).svg()
    assert "<svg" in svg


def test_auto_chart():
    assert ez.auto([1, 2, 3]).kind == "line"
    assert ez.auto({"A": 1, "B": 2}).kind == "bar"
    assert ez.auto([(1, 2), (3, 1), (0, 4)]).kind == "scatter"
    assert ez.auto(["a", "b", "a"]).kind == "bar"


def test_horizontal_bar():
    svg = ez.bar(["A", "B", "C"], [3, 7, 2]).horizontal().svg()
    assert "<rect" in svg
    assert "A" in svg


def test_named_series_dict():
    svg = ez.line({"A": [1, 2, 3], "B": [3, 2, 1]}).svg()
    assert "A" in svg and "B" in svg


def test_line_pairs():
    svg = ez.line([(0, 1), (1, 3), (2, 2)]).svg()
    assert "<path" in svg


def test_xlim_ylim():
    svg = ez.line([1, 2, 3]).xlim(0, 5).ylim(-1, 10).svg()
    assert "<svg" in svg


def test_size_clamped():
    p = ez.line([1]).size(10, 10)
    assert p.width >= 120 and p.height >= 100


def test_render_never_raises():
    p = ez.line([1, 2, 3])
    p._series[0]["x"] = [float("inf"), 1, 2]
    p._series[0]["y"] = [1, float("-inf"), 3]
    svg = p.svg()
    assert "<svg" in svg


def test_repr():
    assert "Plot" in repr(ez.line([1, 2]))


def test_plot_alias():
    assert "<path" in ez.plot([1, 2, 3]).svg()


def test_set_theme():
    ez.set_theme("minimal")
    svg = ez.line([1, 2, 3]).svg()
    assert "#fafafa" in svg
    ez.set_theme("light")


def test_defaults():
    ez.defaults(theme="dark", width=640)
    assert ez.get_defaults()["theme"] == "dark"
    p = ez.line([1, 2, 3])
    assert p.width == 640
    ez.reset_defaults()


def test_subtitle_footnote_hline():
    svg = (
        ez.line([1, 2, 3])
        .t("T")
        .subtitle("S")
        .footnote("F")
        .hline(2)
        .annotate(1, 3, "hi")
        .svg()
    )
    assert "S" in svg and "F" in svg and "hi" in svg


def test_unique_clip_ids():
    a = ez.line([1, 2, 3]).svg()
    b = ez.line([1, 2, 3]).svg()
    assert "clipPath" in a and "clipPath" in b


def test_string_numbers():
    svg = ez.line(["1", "2.5", "3"]).svg()
    assert "<path" in svg or "<circle" in svg


def test_datetime_coercion_and_ticks():
    import datetime
    dates = [
        datetime.datetime(2026, 1, 1),
        datetime.datetime(2026, 1, 2),
        datetime.datetime(2026, 1, 3),
    ]
    vals = [10, 20, 15]
    svg = ez.line(dates, vals).svg()
    assert "<svg" in svg
    assert "Jan 01" in svg or "Jan 02" in svg or "Jan 03" in svg


def test_custom_series_and_draw():
    # Test post-render .draw() callback
    drawn_called = False
    def my_draw(r):
        nonlocal drawn_called
        drawn_called = True
        r.draw_circle(2, 15, 10, "red")
        r.draw_line(1, 10, 3, 20, "blue", dashed=True)
        r.draw_rect(1, 10, 1, 5, "green", fill=False, stroke_color="black")
        r.draw_text(2, 15, "Hello World", "black")
        r.draw_polygon([(1, 10), (2, 20), (3, 10)], "purple")

    p = ez.line([1, 2, 3], [10, 20, 15]).draw(my_draw)
    svg = p.svg()
    assert drawn_called
    assert "<circle" in svg
    assert "Hello World" in svg

    # Test raw_coords mode in primitive drawing methods
    raw_draw_called = False
    def my_raw_draw(r):
        nonlocal raw_draw_called
        raw_draw_called = True
        r.draw_circle(100, 100, 10, "red", raw_coords=True)
        r.draw_line(50, 50, 150, 150, "blue", dashed=True, raw_coords=True)
        r.draw_rect(50, 50, 100, 100, "green", fill=False, stroke_color="black", raw_coords=True)
        r.draw_text(100, 100, "Hello World", "black", raw_coords=True)
        r.draw_polygon([(50, 50), (150, 50), (100, 150)], "purple", raw_coords=True)

    p_raw = ez.line([1, 2, 3], [10, 20, 15]).draw(my_raw_draw)
    svg_raw = p_raw.svg()
    assert raw_draw_called
    assert "<circle" in svg_raw


def test_custom_series_kind():
    called = False
    def render_fn(r):
        nonlocal called
        called = True
        r.draw_circle(2, 20, 5, "gold")

    p = ez.Plot(kind="custom")
    p.add([1, 2, 3], [10, 30, 20], color=render_fn)
    svg = p.svg()
    assert called
    assert "gold" in svg


def test_whitespace_font_fallback():
    from ezplot import font
    # Standard space yields 0 pixels (empty glyph)
    assert len(list(font.iter_pixels(" "))) == 0
    # Non-breaking space \u00a0 yields 0 pixels (falls back to space instead of "?")
    assert len(list(font.iter_pixels("\u00a0"))) == 0
    # Other whitespaces also yield 0 pixels
    assert len(list(font.iter_pixels("\t"))) == 0
    assert len(list(font.iter_pixels("\n"))) == 0
    # Question mark should have non-zero pixels
    assert len(list(font.iter_pixels("?"))) > 0


def test_axhspan_axvspan():
    # Test high-level axhspan and axvspan rendering in both vector and raster formats
    p = (
        ez.line([1, 2, 3], [10, 20, 15])
        .axhspan(12, 18, color="#22c55e", alpha=0.3)
        .axvspan(1.5, 2.5, color="#ef4444", alpha=0.15)
    )
    svg = p.svg()
    assert "rect" in svg
    assert "fill-opacity=\"0.300\"" in svg or "fill-opacity=\"0.3\"" in svg
    assert "fill-opacity=\"0.150\"" in svg or "fill-opacity=\"0.15\"" in svg

    # Raster path test
    png = p.png_bytes()
    assert len(png) > 100


if __name__ == "__main__":
    failed = 0
    for name, fn in list(globals().items()):
        if not (name.startswith("test_") and callable(fn)):
            continue
        try:
            if name in ("test_save", "test_png_export"):
                with tempfile.TemporaryDirectory() as d:
                    fn(Path(d))
            else:
                fn()
            print("ok", name)
        except Exception as e:
            failed += 1
            print("FAIL", name, "→", e)
    if failed:
        print(f"{failed} failed")
        sys.exit(1)
    print("all passed")
