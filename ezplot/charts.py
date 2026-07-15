"""
One-liner chart factories — least typing possible.

    import ezplot as ez

    ez.line([1, 3, 2, 5], t="Hi", save="out.png")
    ez.bar({"A": 10, "B": 20}, t="Sales", save="sales.jpg")
    ez.auto(data, save="chart.png")
    ez.quick([1, 2, 3, 5])                  # auto + show
"""

from __future__ import annotations

from typing import Any, Sequence

from . import utils
from .core import Plot


def line(
    x: Any = None,
    y: Any = None,
    *more: Any,
    label: str | Sequence[str] | None = None,
    labels: Sequence[str] | None = None,
    save: str | None = None,
    **style,
) -> Plot:
    """
    Line chart.

        ez.line([1, 3, 2, 5])
        ez.line(x, y, t="Growth", save="g.png")
        ez.line(x, [y1, y2], labels=["A", "B"])
        ez.line(y1, y2, y3)                    # multi series, shared index
        ez.line([(0,1), (1,3), (2,2)])
        ez.line({"A": [1,2], "B": [2,1]})
    """
    if more:
        series = [x, y, *more] if y is not None else [x, *more]
        if (
            len(series) >= 2
            and utils.looks_numeric_sequence(series[0])
            and all(utils.looks_numeric_sequence(s) for s in series[1:])
            and all(
                len(utils.as_list(s)) == len(utils.as_list(series[0])) for s in series[1:]
            )
        ):
            # first = x, rest = y series
            x, y = series[0], list(series[1:])
        else:
            x, y = None, list(series) if len(series) > 1 else series[0]

    p = Plot(kind="line")
    labs = _labels(label, labels)
    if y is None and x is not None and not isinstance(x, dict) and not utils.is_list_of_pairs(x):
        p._set_xy(None, x, labels=labs)
    else:
        p._set_xy(x, y, labels=labs)
    return _finish(p, style, save)


def plot(x: Any = None, y: Any = None, **kwargs) -> Plot:
    """Alias for `line`."""
    return line(x, y, **kwargs)


def scatter(
    x: Any = None,
    y: Any = None,
    *,
    label: str | Sequence[str] | None = None,
    labels: Sequence[str] | None = None,
    save: str | None = None,
    **style,
) -> Plot:
    """
        ez.scatter(x, y, t="Pts", save="s.png")
        ez.scatter([(1,2), (3,4), (2,5)])
    """
    p = Plot(kind="scatter")
    labs = _labels(label, labels)
    if y is None and x is not None and not isinstance(x, dict) and not utils.is_list_of_pairs(x):
        p._set_xy(None, x, labels=labs)
    else:
        p._set_xy(x, y, labels=labs)
    return _finish(p, style, save)


def area(
    x: Any = None,
    y: Any = None,
    *,
    label: str | Sequence[str] | None = None,
    labels: Sequence[str] | None = None,
    save: str | None = None,
    **style,
) -> Plot:
    """Filled area chart."""
    p = Plot(kind="area")
    labs = _labels(label, labels)
    if y is None and x is not None and not isinstance(x, dict) and not utils.is_list_of_pairs(x):
        p._set_xy(None, x, labels=labs)
    else:
        p._set_xy(x, y, labels=labs)
    return _finish(p, style, save)


def bar(
    categories: Any = None,
    values: Any = None,
    *,
    label: str | Sequence[str] | None = None,
    labels: Sequence[str] | None = None,
    save: str | None = None,
    **style,
) -> Plot:
    """
        ez.bar([10, 25, 15], t="Easy", save="b.png")
        ez.bar(["A","B","C"], [10, 25, 15])
        ez.bar({"A": 10, "B": 25, "C": 15})
        ez.bar(["cat","dog","cat"])          # frequency
    """
    p = Plot(kind="bar")
    labs = _labels(label, labels)
    p._set_bar(categories, values, labels=labs)
    return _finish(p, style, save)


def hist(
    data: Any,
    bins: int | None = None,
    *,
    save: str | None = None,
    **style,
) -> Plot:
    """`ez.hist(samples, 20, t="Dist", save="h.png")`"""
    p = Plot(kind="hist")
    p._set_hist(data, bins=bins)
    return _finish(p, style, save)


def pie(
    values: Any,
    labels: Sequence[str] | None = None,
    *,
    save: str | None = None,
    **style,
) -> Plot:
    """
        ez.pie([30, 20, 50], ["A","B","C"], save="p.png")
        ez.pie({"A": 30, "B": 20}, donut=True, save="d.png")
    """
    p = Plot(kind="pie")
    p._set_pie(values, labels=labels)
    return _finish(p, style, save)


def auto(
    data: Any,
    y: Any = None,
    *,
    save: str | None = None,
    **style,
) -> Plot:
    """
    Smart chart — picks line / bar / scatter from the data.

        ez.auto([1, 3, 2, 5], save="a.png")
        ez.auto({"A": 10, "B": 20})
        ez.auto([(1,2), (3,1), (4,4)])
    """
    kind = utils.infer_chart_kind(data, y)

    if (
        y is None
        and not isinstance(data, dict)
        and not utils.looks_numeric_sequence(data)
        and not utils.is_list_of_pairs(data)
    ):
        return bar(data, save=save, **style)

    if kind == "bar":
        if isinstance(data, dict):
            return bar(data, save=save, **style)
        return bar(data, y, save=save, **style)
    if kind == "scatter":
        return scatter(data, y, save=save, **style)
    return line(data, y, save=save, **style)


def quick(data: Any, y: Any = None, *, save: str | None = None, show: bool = True, **style) -> Plot:
    """
    Fastest path: auto-detect chart + optional save + show.

        ez.quick([1, 3, 2, 5])
        ez.quick({"A": 10, "B": 20}, t="Sales", theme="dark")
        ez.quick(x, y, save="out.png")
    """
    p = auto(data, y, save=save, **style)
    if show:
        try:
            p.show()
        except Exception:
            pass
    return p


# ---- helpers -------------------------------------------------------------

_STYLE_MAP = {
    "title": "title",
    "t": "title",
    "xlabel": "xlabel",
    "xlab": "xlabel",
    "ylabel": "ylabel",
    "ylab": "ylabel",
    "color": "color",
    "c": "color",
    "palette": "palette",
    "theme": "theme",
    "grid": "grid",
    "legend": "legend",
    "markers": "markers",
    "dashed": "dashed",
    "alpha": "alpha",
    "point_size": "point_size",
    "s": "point_size",
    "linewidth": "linewidth",
    "lw": "linewidth",
    "donut": "donut",
    "horizontal": "horizontal",
    "hbar": "horizontal",
    "values": "values",
    "sort": "sort",
    "subtitle": "subtitle",
    "footnote": "footnote",
    "stacked": "stacked",
    "fill": "fill",
    "logy": "logy",
    "logx": "logx",
    "tight": "tight",
    "dpi": "dpi",
    "legend_pos": "legend_pos",
    "bg": "bg",
}


def _finish(p: Plot, style: dict, save: str | None) -> Plot:
    # pull save out of style too
    path = save or style.pop("save", None)
    p = _apply_style(p, style)
    if path:
        p.save(path)
    return p


def _apply_style(p: Plot, style: dict) -> Plot:
    if "size" in style and isinstance(style["size"], (list, tuple)) and len(style["size"]) == 2:
        p.size(style["size"][0], style["size"][1])
    if any(k in style for k in ("width", "w", "height", "h")):
        p.size(
            style.get("width", style.get("w", p.width)),
            style.get("height", style.get("h", p.height)),
        )

    if "xlim" in style and isinstance(style["xlim"], (list, tuple)) and len(style["xlim"]) == 2:
        p.xlim(style["xlim"][0], style["xlim"][1])
    if "ylim" in style and isinstance(style["ylim"], (list, tuple)) and len(style["ylim"]) == 2:
        p.ylim(style["ylim"][0], style["ylim"][1])
    if "quality" in style or "q" in style:
        try:
            p._quality = int(style.get("quality", style.get("q", 90)))
        except (TypeError, ValueError):
            pass
    if "colors" in style and isinstance(style["colors"], (list, tuple)):
        p.colors(*style["colors"])
    # axis label shortcuts that conflict with series x/y — only if string
    if "x" in style and isinstance(style["x"], str):
        p.xlabel(style["x"])
    if "y" in style and isinstance(style["y"], str):
        p.ylabel(style["y"])

    for key, method in _STYLE_MAP.items():
        if key in style and hasattr(p, method):
            getattr(p, method)(style[key])
    return p


def _labels(
    label: str | Sequence[str] | None,
    labels: Sequence[str] | None,
) -> list[str] | None:
    if labels is not None:
        return list(labels)
    if label is None:
        return None
    if isinstance(label, str):
        return [label]
    return list(label)
