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

    Positional multi-argument calls are resolved intelligently:
    if the first argument looks like an index/axis (0,1,2,…) it is used
    as x; otherwise all arguments are treated as parallel y series.
    """
    force_multi = False
    if more:
        series = [x, y, *more] if y is not None else [x, *more]
        if (
            len(series) >= 2
            and utils.looks_numeric_sequence(series[0])
            and all(utils.looks_numeric_sequence(s) for s in series[1:])
        ):
            same_len = all(
                len(utils.as_list(s)) == len(utils.as_list(series[0]))
                for s in series[1:]
            )
            first_like_index = utils.looks_like_index(series[0])
            others_like_index = all(
                utils.looks_like_index(s) for s in series[1:]
            )
            # first = x only when it looks like an index axis and
            # the rest don't all look like indices too (ambiguity → series)
            if same_len and first_like_index and not others_like_index:
                x, y = series[0], list(series[1:])
            else:
                x, y = None, list(series)
                force_multi = True
        else:
            x, y = None, list(series) if len(series) > 1 else series[0]
            force_multi = len(series) > 1

    p = Plot(kind="line")
    labs = _labels(label, labels)
    if y is None and x is not None and not isinstance(x, dict) and not utils.is_list_of_pairs(x):
        p._set_xy(None, x, labels=labs)
    else:
        p._set_xy(x, y, labels=labs, force_multi=force_multi)
    return _finish(p, style, save)


def plot(x: Any = None, y: Any = None, *more: Any, **kwargs) -> Plot:
    """Alias for `line`."""
    return line(x, y, *more, **kwargs)


def scatter(
    x: Any = None,
    y: Any = None,
    *more: Any,
    label: str | Sequence[str] | None = None,
    labels: Sequence[str] | None = None,
    save: str | None = None,
    **style,
) -> Plot:
    """
        ez.scatter(x, y, t="Pts", save="s.png")
        ez.scatter([(1,2), (3,4), (2,5)])
        ez.scatter(x, y1, y2)          # multi series, like line()
    """
    force_multi = False
    if more:
        series = [x, y, *more] if y is not None else [x, *more]
        if (
            len(series) >= 2
            and utils.looks_numeric_sequence(series[0])
            and all(utils.looks_numeric_sequence(s) for s in series[1:])
        ):
            same_len = all(
                len(utils.as_list(s)) == len(utils.as_list(series[0]))
                for s in series[1:]
            )
            if same_len and utils.looks_like_index(series[0]) and not all(
                utils.looks_like_index(s) for s in series[1:]
            ):
                x, y = series[0], list(series[1:])
            else:
                x, y = None, list(series)
                force_multi = True
        else:
            x, y = None, list(series) if len(series) > 1 else series[0]
            force_multi = len(series) > 1

    p = Plot(kind="scatter")
    labs = _labels(label, labels)
    if y is None and x is not None and not isinstance(x, dict) and not utils.is_list_of_pairs(x):
        p._set_xy(None, x, labels=labs)
    else:
        p._set_xy(x, y, labels=labs, force_multi=force_multi)
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
    *more: Any,
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
        ez.bar(["A","B"], [1,2], [3,4])      # grouped series
        ez.bar({"A": 10, "B": 20}, values=True)   # dict + value labels
    """
    if isinstance(values, bool):
        # `values=True/False` here is the value-label toggle, not data
        style.setdefault("values", values)
        values = None
    p = Plot(kind="bar")
    labs = _labels(label, labels)
    if more:
        series_vals = [values, *more]
        p._set_bar(categories, series_vals, labels=labs)
    else:
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


def donut(
    values: Any,
    labels: Sequence[str] | None = None,
    *,
    save: str | None = None,
    **style,
) -> Plot:
    """Donut chart — shortcut for `ez.pie(..., donut=True)`."""
    style.setdefault("donut", True)
    return pie(values, labels=labels, save=save, **style)


def barh(
    categories: Any = None,
    vals: Any = None,
    *more: Any,
    save: str | None = None,
    **style,
) -> Plot:
    """
    Horizontal bars — shortcut for `ez.bar(..., horizontal=True)`.

    The second positional argument is named `vals` so that the
    `values=True/False` label toggle keeps working as a keyword:

        ez.barh(["A", "B"], [3, 7], values=True, t="Scores")
    """
    if isinstance(vals, bool):
        style.setdefault("values", vals)
        vals = None
    style.setdefault("horizontal", True)
    # `values` is bar's data parameter — pass the toggle separately
    toggle = style.pop("values", None)
    p = bar(categories, vals, *more, save=save, **style)
    if toggle is not None:
        p.values(toggle)
    return p


def step(
    x: Any = None,
    y: Any = None,
    *,
    label: str | Sequence[str] | None = None,
    labels: Sequence[str] | None = None,
    save: str | None = None,
    **style,
) -> Plot:
    """
    Step chart — values hold until the next x.

        ez.step([0, 1, 2, 3], [0, 2, 1, 3], t="Steps", save="s.png")
    """
    p = Plot(kind="line")
    labs = _labels(label, labels)
    if y is None and x is not None and not isinstance(x, dict) and not utils.is_list_of_pairs(x):
        p._set_xy(None, x, labels=labs)
    else:
        p._set_xy(x, y, labels=labs)
    p.step(True)
    return _finish(p, style, save)


def boxplot(
    data: Any,
    labels: Sequence[str] | None = None,
    *,
    save: str | None = None,
    **style,
) -> Plot:
    """
    Box plot with Tukey whiskers (1.5·IQR) and outlier dots.

        ez.boxplot([1, 2, 3, 4, 5, 20], t="Single box")
        ez.boxplot([[1,2,3], [2,4,8], [5,6,7]], labels=["A", "B", "C"])
        ez.boxplot({"A": [...], "B": [...]})
    """
    p = Plot(kind="box")
    p._set_box(data, labels=labels)
    return _finish(p, style, save)


def box(data: Any, labels: Sequence[str] | None = None, **kwargs) -> Plot:
    """Alias for `boxplot`."""
    return boxplot(data, labels=labels, **kwargs)


def heatmap(
    matrix: Any,
    *,
    row_labels: Sequence[str] | None = None,
    col_labels: Sequence[str] | None = None,
    cmap: str = "blues",
    show_values: bool = True,
    colorbar: bool = True,
    save: str | None = None,
    **style,
) -> Plot:
    """
    Heatmap of a 2D matrix (list of lists / numpy array).

        ez.heatmap([[1, 2, 3], [4, 5, 6], [7, 8, 9]],
                   row_labels=["a", "b", "c"],
                   col_labels=["x", "y", "z"],
                   t="Matrix", save="heat.png")
    """
    p = Plot(kind="heat")
    p._set_heat(
        matrix,
        row_labels=row_labels,
        col_labels=col_labels,
        cmap=cmap,
        show_values=show_values,
        colorbar=colorbar,
    )
    return _finish(p, style, save)


def function(
    fn: Any,
    start: float,
    end: float,
    steps: int = 200,
    *,
    save: str | None = None,
    **style,
) -> Plot:
    """
    Plot any Python callable over [start, end].

        ez.function(lambda x: x ** 2, -5, 5, t="x²", save="f.png")
    """
    steps = max(2, int(steps))
    xs = [start + (end - start) * i / (steps - 1) for i in range(steps)]
    ys = [fn(x) for x in xs]
    p = Plot(kind="line")
    p._set_xy(xs, ys)
    p.markers(False)
    return _finish(p, style, save)


def fn(fn: Any, start: float, end: float, steps: int = 200, **kwargs) -> Plot:
    """Alias for `function`."""
    return function(fn, start, end, steps, **kwargs)


def chart(*args: Any, **kwargs: Any) -> Plot:
    """Alias for `auto`."""
    return auto(*args, **kwargs)


def auto(
    data: Any,
    y: Any = None,
    *,
    save: str | None = None,
    **style,
) -> Plot:
    """
    Smart chart — picks line / bar / scatter / heatmap from the data.

        ez.auto([1, 3, 2, 5], save="a.png")
        ez.auto({"A": 10, "B": 20})
        ez.auto([(1,2), (3,1), (4,4)])
        ez.auto([[1, 2, 3], [4, 5, 6], [7, 8, 9]])   # heatmap
    """
    kind = utils.infer_chart_kind(data, y)

    if kind == "heatmap":
        return heatmap(data, save=save, **style)

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
    "xrot": "xrot",
    "rotate": "xrot",
    "step": "step",
    "trend": "trend",
    "smooth": "smooth",
    "yerr": "yerr",
    "xerr": "xerr",
}

# keys _apply_style understands (outside _STYLE_MAP) — used to warn on typos
_EXTRA_STYLE_KEYS = {
    "size", "width", "w", "height", "h", "xlim", "ylim",
    "quality", "q", "colors", "x", "y", "save",
    "xticks", "yticks",
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
    if "xticks" in style:
        p.xticks(style["xticks"])
    if "yticks" in style:
        p.yticks(style["yticks"])

    unknown = [
        k for k in style
        if k not in _STYLE_MAP and k not in _EXTRA_STYLE_KEYS
    ]
    if unknown:
        import warnings
        names = ', '.join(sorted(map(str, unknown)))
        p._emit("warning", "ezplot.style.unknown_option", "Unknown style option(s) ignored", options=names)
        warnings.warn(
            f"ezplot: unknown style option(s) ignored: {names}",
            UserWarning,
            stacklevel=3,
        )

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
