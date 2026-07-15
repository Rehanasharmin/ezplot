"""
Plot — the fluent, chainable chart object.

Every style method returns `self`:

    ez.line(y).title("Hi").color("coral").save("out.svg").show()
"""

from __future__ import annotations

import math
import os
import tempfile
import webbrowser
from pathlib import Path
from typing import Any, Sequence

from . import utils
from .render import SVGRenderer
from .style import get_theme, get_palette

# raster formats
_RASTER_EXTS = {".png", ".jpg", ".jpeg", ".jpe", ".webp", ".bmp", ".tif", ".tiff", ".gif"}
_JPEG_EXTS = {".jpg", ".jpeg", ".jpe"}


class Plot:
    """A single chart. Prefer factories: `ez.line`, `ez.bar`, `ez.auto`, …"""

    def __init__(
        self,
        kind: str = "line",
        width: int = 720,
        height: int = 420,
        theme: str | None = None,
    ):
        self.kind = kind
        self.width = max(120, int(width))
        self.height = max(100, int(height))
        self._theme_name = theme
        self._title = ""
        self._xlabel = ""
        self._ylabel = ""
        self._color: str | None = None
        self._palette: str | None = None
        self._grid = True
        self._legend = True
        self._markers: bool | None = None  # None = auto
        self._dashed = False
        self._alpha = 0.85
        self._size = 5.0
        self._linewidth = 2.5
        self._donut = False
        self._bins: int | None = None
        self._horizontal = False
        self._show_values = False
        self._sort_x = False
        self._quality = 90  # jpeg/webp quality
        self._subtitle = ""
        self._footnote = ""
        self._stacked = False
        self._fill = True  # area fill
        self._logy = False
        self._logx = False
        self._tight = False
        self._dpi = 1
        self._legend_pos = "top-right"
        self._font_scale = 1
        self._bg_override = None
        self._annotations: list[dict[str, Any]] = []
        self._hlines: list[dict[str, Any]] = []
        self._vlines: list[dict[str, Any]] = []
        self._margin_override: dict | None = None
        self._yticks: list[float] | None = None
        self._xticks: list[float] | None = None

        self._series: list[dict[str, Any]] = []
        self._categories: list[str] | None = None
        self._xlim: tuple[float, float] | None = None
        self._ylim: tuple[float, float] | None = None
        self._svg: str | None = None
        self._raster = None  # cached Canvas

        # apply process-wide defaults (non-destructive)
        try:
            from .config import get_defaults
            d = get_defaults()
            if d.get("theme") is not None and theme is None:
                self._theme_name = d["theme"]
            if width == 720:
                self.width = max(120, int(d.get("width", 720)))
            if height == 420:
                self.height = max(100, int(d.get("height", 420)))
            self._quality = int(d.get("quality", 90))
            self._grid = bool(d.get("grid", True))
            self._legend = bool(d.get("legend", True))
            self._markers = d.get("markers", None)
            self._linewidth = float(d.get("linewidth", 2.5))
            self._size = float(d.get("point_size", 5.0))
            self._alpha = float(d.get("alpha", 0.85))
            if d.get("palette"):
                self._palette = d["palette"]
            self._dpi = max(1, int(d.get("dpi", 1)))
            self._tight = bool(d.get("tight", False))
            self._legend_pos = d.get("legend_pos") or "top-right"
            self._font_scale = max(1, int(d.get("font_scale", 1)))
            if d.get("bg"):
                self._bg_override = d["bg"]
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # fluent style
    # ------------------------------------------------------------------ #

    def _dirty(self) -> "Plot":
        self._svg = None
        self._raster = None
        return self

    def title(self, text: Any) -> "Plot":
        self._title = "" if text is None else str(text)
        return self._dirty()

    def t(self, text: Any) -> "Plot":
        """Shortcut for .title()."""
        return self.title(text)

    def xlabel(self, text: Any) -> "Plot":
        self._xlabel = "" if text is None else str(text)
        return self._dirty()

    def ylabel(self, text: Any) -> "Plot":
        self._ylabel = "" if text is None else str(text)
        return self._dirty()

    def labels(self, x: str = "", y: str = "") -> "Plot":
        if x:
            self._xlabel = str(x)
        if y:
            self._ylabel = str(y)
        return self._dirty()

    def style(self, **kw: Any) -> "Plot":
        """
        Set many options at once (super short).

            p.style(t="Sales", color="coral", theme="dark", w=800, h=400)
        """
        alias = {
            "t": "title",
            "title": "title",
            "x": "xlabel",
            "xlabel": "xlabel",
            "xlab": "xlabel",
            "y": "ylabel",
            "ylabel": "ylabel",
            "ylab": "ylabel",
            "c": "color",
            "color": "color",
            "colours": "colors",
            "colors": "colors",
            "palette": "palette",
            "theme": "theme",
            "w": "width",
            "width": "width",
            "h": "height",
            "height": "height",
            "grid": "grid",
            "legend": "legend",
            "markers": "markers",
            "dashed": "dashed",
            "alpha": "alpha",
            "point_size": "point_size",
            "s": "point_size",
            "lw": "linewidth",
            "linewidth": "linewidth",
            "donut": "donut",
            "horizontal": "horizontal",
            "hbar": "horizontal",
            "values": "values",
            "sort": "sort",
            "quality": "quality",
            "q": "quality",
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
            "font_scale": "font_scale",
        }
        # size pair
        if "size" in kw and isinstance(kw["size"], (list, tuple)) and len(kw["size"]) == 2:
            self.size(kw["size"][0], kw["size"][1])
        if "width" in kw or "w" in kw or "height" in kw or "h" in kw:
            self.size(kw.get("width", kw.get("w", self.width)), kw.get("height", kw.get("h", self.height)))
        if "xlim" in kw and isinstance(kw["xlim"], (list, tuple)) and len(kw["xlim"]) == 2:
            self.xlim(kw["xlim"][0], kw["xlim"][1])
        if "ylim" in kw and isinstance(kw["ylim"], (list, tuple)) and len(kw["ylim"]) == 2:
            self.ylim(kw["ylim"][0], kw["ylim"][1])
        if "labels" in kw and isinstance(kw["labels"], (list, tuple)) and len(kw["labels"]) == 2:
            self.labels(kw["labels"][0], kw["labels"][1])

        for k, v in kw.items():
            key = alias.get(k)
            if key is None:
                continue
            if key in ("width", "height", "quality"):
                if key == "quality":
                    try:
                        self._quality = int(v)
                    except (TypeError, ValueError):
                        pass
                continue
            if key == "colors":
                if isinstance(v, (list, tuple)):
                    self.colors(*v)
                continue
            if key == "title":
                self.title(v)
            elif key == "xlabel":
                self.xlabel(v)
            elif key == "ylabel":
                self.ylabel(v)
            elif key == "color":
                self.color(v)
            elif key == "palette":
                self.palette(v)
            elif key == "theme":
                self.theme(v)
            elif key == "grid":
                self.grid(v)
            elif key == "legend":
                self.legend(v)
            elif key == "markers":
                self.markers(v)
            elif key == "dashed":
                self.dashed(v)
            elif key == "alpha":
                self.alpha(v)
            elif key == "point_size":
                self.point_size(v)
            elif key == "linewidth":
                self.linewidth(v)
            elif key == "donut":
                self.donut(v)
            elif key == "horizontal":
                self.horizontal(v)
            elif key == "values":
                self.values(v)
            elif key == "sort":
                self.sort(v)
            elif key == "subtitle":
                self.subtitle(v)
            elif key == "footnote":
                self.footnote(v)
            elif key == "stacked":
                self.stacked(v)
            elif key == "fill":
                self.fill(v)
            elif key == "logy":
                self.logy(v)
            elif key == "logx":
                self.logx(v)
            elif key == "tight":
                self.tight(v)
            elif key == "dpi":
                self.dpi(v)
            elif key == "legend_pos":
                self.legend_pos(v)
            elif key == "bg":
                self.bg(v)
            elif key == "font_scale":
                try:
                    self._font_scale = max(1, int(v))
                    self._dirty()
                except (TypeError, ValueError):
                    pass
        return self

    def color(self, color: str) -> "Plot":
        self._color = str(color) if color is not None else None
        if self._series and self._color:
            self._series[0]["color"] = self._color
        return self._dirty()

    def colors(self, *cols: str) -> "Plot":
        for i, c in enumerate(cols):
            if i < len(self._series):
                self._series[i]["color"] = c
        return self._dirty()

    def palette(self, name: str) -> "Plot":
        self._palette = name
        return self._dirty()

    def theme(self, name: str) -> "Plot":
        self._theme_name = name
        return self._dirty()

    def size(self, width: int = 720, height: int = 420) -> "Plot":
        self.width = max(120, int(width))
        self.height = max(100, int(height))
        return self._dirty()

    def grid(self, on: bool = True) -> "Plot":
        self._grid = bool(on)
        return self._dirty()

    def legend(self, on: bool = True) -> "Plot":
        self._legend = bool(on)
        return self._dirty()

    def markers(self, on: bool = True) -> "Plot":
        self._markers = bool(on)
        return self._dirty()

    def dashed(self, on: bool = True) -> "Plot":
        self._dashed = bool(on)
        return self._dirty()

    def alpha(self, a: float) -> "Plot":
        try:
            self._alpha = min(1.0, max(0.0, float(a)))
        except (TypeError, ValueError):
            pass
        return self._dirty()

    def point_size(self, s: float) -> "Plot":
        try:
            self._size = max(0.5, float(s))
        except (TypeError, ValueError):
            pass
        return self._dirty()

    def linewidth(self, w: float) -> "Plot":
        try:
            self._linewidth = max(0.5, float(w))
        except (TypeError, ValueError):
            pass
        return self._dirty()

    def donut(self, on: bool = True) -> "Plot":
        self._donut = bool(on)
        return self._dirty()

    def horizontal(self, on: bool = True) -> "Plot":
        """Horizontal bars (bar charts only)."""
        self._horizontal = bool(on)
        return self._dirty()

    def values(self, on: bool = True) -> "Plot":
        """Show numeric labels on bars."""
        self._show_values = bool(on)
        return self._dirty()

    def sort(self, on: bool = True) -> "Plot":
        """Sort points by x (line/scatter/area)."""
        self._sort_x = bool(on)
        return self._dirty()

    def subtitle(self, text: Any) -> "Plot":
        self._subtitle = "" if text is None else str(text)
        return self._dirty()

    def footnote(self, text: Any) -> "Plot":
        """Small caption under the chart (source, notes)."""
        self._footnote = "" if text is None else str(text)
        return self._dirty()

    def stacked(self, on: bool = True) -> "Plot":
        """Stack multi-series bars (bar charts)."""
        self._stacked = bool(on)
        return self._dirty()

    def fill(self, on: bool = True) -> "Plot":
        self._fill = bool(on)
        return self._dirty()

    def logy(self, on: bool = True) -> "Plot":
        self._logy = bool(on)
        return self._dirty()

    def logx(self, on: bool = True) -> "Plot":
        self._logx = bool(on)
        return self._dirty()

    def tight(self, on: bool = True) -> "Plot":
        """Reduce margins for denser figures."""
        self._tight = bool(on)
        return self._dirty()

    def dpi(self, scale: int = 2) -> "Plot":
        """Raster scale factor (2 ≈ retina PNG/JPEG)."""
        try:
            self._dpi = max(1, min(4, int(scale)))
        except (TypeError, ValueError):
            pass
        return self._dirty()

    def legend_pos(self, pos: str = "top-right") -> "Plot":
        """Legend corner: top-right, top-left, bottom-right, bottom-left."""
        allowed = {"top-right", "top-left", "bottom-right", "bottom-left", "tr", "tl", "br", "bl"}
        p = str(pos).lower().strip()
        alias = {"tr": "top-right", "tl": "top-left", "br": "bottom-right", "bl": "bottom-left"}
        self._legend_pos = alias.get(p, p if p in allowed else "top-right")
        return self._dirty()

    def bg(self, color: str) -> "Plot":
        """Override background color for this plot."""
        self._bg_override = color
        return self._dirty()

    def margin(self, top: int | None = None, right: int | None = None,
               bottom: int | None = None, left: int | None = None) -> "Plot":
        """Custom plot margins in pixels."""
        m = dict(self._margin_override or {})
        if top is not None:
            m["top"] = int(top)
        if right is not None:
            m["right"] = int(right)
        if bottom is not None:
            m["bottom"] = int(bottom)
        if left is not None:
            m["left"] = int(left)
        self._margin_override = m
        return self._dirty()

    def annotate(self, x: float, y: float, text: str, *,
                 color: str | None = None, anchor: str = "start") -> "Plot":
        """Add a text label at data coordinates."""
        self._annotations.append({
            "x": float(x), "y": float(y), "text": str(text),
            "color": color, "anchor": anchor,
        })
        return self._dirty()

    def hline(self, y: float, *, color: str = "#94a3b8",
              dashed: bool = True, label: str = "", width: float = 1.5) -> "Plot":
        """Horizontal reference line at y."""
        self._hlines.append({
            "y": float(y), "color": color, "dashed": dashed,
            "label": label, "width": width,
        })
        return self._dirty()

    def vline(self, x: float, *, color: str = "#94a3b8",
              dashed: bool = True, label: str = "", width: float = 1.5) -> "Plot":
        """Vertical reference line at x."""
        self._vlines.append({
            "x": float(x), "color": color, "dashed": dashed,
            "label": label, "width": width,
        })
        return self._dirty()

    def xticks(self, ticks: Sequence[float]) -> "Plot":
        self._xticks = [float(t) for t in ticks]
        return self._dirty()

    def yticks(self, ticks: Sequence[float]) -> "Plot":
        self._yticks = [float(t) for t in ticks]
        return self._dirty()

    def configure(self, **kw: Any) -> "Plot":
        """Alias for style() — set many options at once."""
        return self.style(**kw)

    def xlim(self, lo: float, hi: float) -> "Plot":
        try:
            a, b = float(lo), float(hi)
            if math.isfinite(a) and math.isfinite(b):
                self._xlim = (min(a, b), max(a, b))
        except (TypeError, ValueError):
            pass
        return self._dirty()

    def ylim(self, lo: float, hi: float) -> "Plot":
        try:
            a, b = float(lo), float(hi)
            if math.isfinite(a) and math.isfinite(b):
                self._ylim = (min(a, b), max(a, b))
        except (TypeError, ValueError):
            pass
        return self._dirty()

    # ------------------------------------------------------------------ #
    # data API
    # ------------------------------------------------------------------ #

    def add(
        self,
        x: Any = None,
        y: Any = None,
        *,
        label: str = "",
        color: str | None = None,
        kind: str | None = None,
    ) -> "Plot":
        """Add another series. Accepts y-only, x+y, or list-of-pairs."""
        k = kind or self.kind
        lab = label or f"series {len(self._series) + 1}"

        if k in ("bar", "pie"):
            if isinstance(x, dict) and y is None:
                cats, vals = utils.dict_to_xy(x)
            elif y is None and x is not None:
                vals = utils.as_float_list(x)
                cats = [str(i) for i in range(len(vals))]
            else:
                cats = utils.as_str_list(x) if x is not None else []
                vals = utils.as_float_list(y) if y is not None else []
            self._series.append(
                {
                    "kind": k,
                    "categories": cats,
                    "values": vals,
                    "label": lab,
                    "color": color,
                }
            )
        else:
            xs, ys = self._coerce_xy(x, y)
            self._series.append(
                {
                    "kind": k,
                    "x": xs,
                    "y": ys,
                    "label": lab,
                    "color": color,
                }
            )
        return self._dirty()

    @staticmethod
    def _coerce_xy(x: Any, y: Any) -> tuple[list[float], list[float]]:
        """Smart (x,y) coercion for line/scatter/area."""
        # list of pairs: [(x,y), ...]
        if y is None and utils.is_list_of_pairs(x):
            return utils.unpack_pairs(x)

        # y only
        if y is None:
            ys = utils.as_float_list_keep_nan(x)
            xs = [float(i) for i in range(len(ys))]
            return xs, ys

        # multi-y handled by _set_xy; here single series
        if utils.is_list_of_lists(y) and not utils.is_list_of_pairs(y):
            # take first series only in add()
            y = utils.as_list(y)[0]

        ys = utils.as_float_list_keep_nan(y)

        # categorical x → indices (labels stored elsewhere if needed)
        if x is None:
            xs = [float(i) for i in range(len(ys))]
        elif utils.looks_numeric_sequence(x):
            xs = utils.as_float_list_keep_nan(x)
        else:
            # categories as x: use indices
            xs = [float(i) for i in range(len(utils.as_list(x)))]
            # pad/trim
            if len(xs) < len(ys):
                xs = xs + [float(i) for i in range(len(xs), len(ys))]
            xs = xs[: len(ys)]

        n = min(len(xs), len(ys))
        return xs[:n], ys[:n]

    def _set_xy(
        self,
        x: Any,
        y: Any,
        labels: Sequence[str] | None = None,
    ) -> "Plot":
        """Used by line/scatter/area factories. Supports multi-y + pairs + dicts."""
        # dict of series: {"A": [..], "B": [..]} with shared x or index
        if isinstance(y, dict):
            keys = list(y.keys())
            series_list = [utils.as_float_list_keep_nan(y[k]) for k in keys]
            labs = labels or [str(k) for k in keys]
            max_n = max((len(s) for s in series_list), default=0)
            if x is None:
                xs = [float(i) for i in range(max_n)]
            else:
                xs = utils.as_float_list_keep_nan(x)
            self._series = []
            for i, ys in enumerate(series_list):
                n = min(len(xs), len(ys)) if xs else len(ys)
                xx = xs[:n] if xs else [float(j) for j in range(n)]
                self._series.append(
                    {
                        "kind": self.kind,
                        "x": xx,
                        "y": ys[:n],
                        "label": labs[i] if i < len(labs) else f"y{i+1}",
                        "color": None,
                    }
                )
            return self

        if isinstance(x, dict) and y is None:
            # treat as named series of y values (index x)
            return self._set_xy(None, x, labels=labels)

        # list of pairs
        if y is None and utils.is_list_of_pairs(x):
            xs, ys = utils.unpack_pairs(x)
            self._series = [
                {
                    "kind": self.kind,
                    "x": xs,
                    "y": ys,
                    "label": (labels[0] if labels else "y"),
                    "color": self._color,
                }
            ]
            return self

        if y is None:
            ys = utils.as_float_list_keep_nan(x)
            xs = [float(i) for i in range(len(ys))]
            self._series = [
                {
                    "kind": self.kind,
                    "x": xs,
                    "y": ys,
                    "label": (labels[0] if labels else "y"),
                    "color": self._color,
                }
            ]
            return self

        y_raw = utils.as_list(y)
        multi = utils.is_list_of_lists(y) and not utils.is_list_of_pairs(y)
        # also: numpy 2d
        if hasattr(y, "ndim") and getattr(y, "ndim", 1) >= 2:
            multi = True
            y_raw = utils.as_list(y)

        if multi:
            ys_list = [utils.as_float_list_keep_nan(s) for s in y_raw]
        else:
            ys_list = [utils.as_float_list_keep_nan(y)]

        if x is None:
            max_n = max((len(s) for s in ys_list), default=0)
            xs_full = [float(i) for i in range(max_n)]
        elif utils.looks_numeric_sequence(x):
            xs_full = utils.as_float_list_keep_nan(x)
        else:
            # categorical x — map to indices, remember labels for ticks later
            cats = utils.as_str_list(x)
            self._categories = cats
            xs_full = [float(i) for i in range(len(cats))]

        self._series = []
        for i, ys in enumerate(ys_list):
            n = min(len(xs_full), len(ys))
            if n == 0 and len(ys) > 0:
                xs = [float(j) for j in range(len(ys))]
                n = len(ys)
                xx, yy = xs, ys
            else:
                xx, yy = xs_full[:n], ys[:n]
            lab = (
                labels[i]
                if labels and i < len(labels)
                else (f"y{i+1}" if len(ys_list) > 1 else "y")
            )
            self._series.append(
                {
                    "kind": self.kind,
                    "x": list(xx),
                    "y": list(yy),
                    "label": lab,
                    "color": None,
                }
            )
        return self

    def _set_bar(
        self,
        categories: Any,
        values: Any = None,
        labels: Sequence[str] | None = None,
    ) -> "Plot":
        # dict: {cat: value} or {cat: [v1,v2]} 
        if isinstance(categories, dict) and values is None:
            cats, vals = utils.dict_to_xy(categories)
            self._categories = cats
            self._series = [
                {
                    "kind": "bar",
                    "categories": cats,
                    "values": vals,
                    "label": labels[0] if labels else "values",
                    "color": self._color,
                }
            ]
            return self

        if values is None:
            # smart: if looks like categories (strings), empty values
            # if numeric → values with index cats
            if categories is None:
                self._series = []
                return self
            if utils.looks_numeric_sequence(categories) or utils.is_list_of_lists(categories):
                if utils.is_list_of_lists(categories):
                    # bar([[a,b],[c,d]]) → grouped with index cats
                    series_vals = [utils.as_float_list(s) for s in utils.as_list(categories)]
                    n = max((len(s) for s in series_vals), default=0)
                    cats = [str(i) for i in range(n)]
                    self._categories = cats
                    self._series = []
                    for i, vals in enumerate(series_vals):
                        lab = (
                            labels[i]
                            if labels and i < len(labels)
                            else f"s{i+1}"
                        )
                        self._series.append(
                            {
                                "kind": "bar",
                                "categories": cats,
                                "values": utils.pad_series(vals, n),
                                "label": lab,
                                "color": None,
                            }
                        )
                    return self
                vals = utils.as_float_list(categories)
                cats = [str(i) for i in range(len(vals))]
            else:
                # list of strings alone → count frequency
                items = utils.as_str_list(categories)
                freq: dict[str, float] = {}
                for it in items:
                    freq[it] = freq.get(it, 0.0) + 1.0
                cats = list(freq.keys())
                vals = list(freq.values())
                if not self._ylabel:
                    self._ylabel = "count"
            self._categories = cats
            self._series = [
                {
                    "kind": "bar",
                    "categories": cats,
                    "values": vals,
                    "label": labels[0] if labels else "values",
                    "color": self._color,
                }
            ]
            return self

        cats = utils.as_str_list(categories)
        self._categories = cats
        n = len(cats)

        if isinstance(values, dict):
            # {series_name: [values...]}
            keys = list(values.keys())
            series_vals = [utils.pad_series(utils.as_float_list(values[k]), n) for k in keys]
            labs = labels or [str(k) for k in keys]
        elif utils.is_list_of_lists(values):
            series_vals = [
                utils.pad_series(utils.as_float_list(s), n) for s in utils.as_list(values)
            ]
            labs = list(labels) if labels else None
        else:
            series_vals = [utils.pad_series(utils.as_float_list(values), n)]
            labs = list(labels) if labels else None

        self._series = []
        for i, vals in enumerate(series_vals):
            lab = (
                labs[i]
                if labs and i < len(labs)
                else (f"s{i+1}" if len(series_vals) > 1 else "values")
            )
            self._series.append(
                {
                    "kind": "bar",
                    "categories": cats,
                    "values": vals,
                    "label": lab,
                    "color": None,
                }
            )
        return self

    def _set_hist(self, data: Any, bins: int | None = None) -> "Plot":
        raw = utils.as_list(data)
        # flatten one level if needed
        if raw and isinstance(raw[0], (list, tuple)):
            flat: list[Any] = []
            for row in raw:
                flat.extend(utils.as_list(row))
            raw = flat
        values = [f for f in (utils.to_float(v) for v in raw) if f is not None]
        self._bins = bins
        edges, centers, counts = utils.histogram_bins(values, bins)
        self.kind = "bar"
        # use nicer labels from edges midpoints
        self._categories = [utils.format_number(c) for c in centers]
        self._series = [
            {
                "kind": "bar",
                "categories": self._categories,
                "values": counts,
                "label": "count",
                "color": self._color,
                "_hist_centers": centers,
                "_hist_edges": edges,
                "_hist_raw": values,
            }
        ]
        if not self._xlabel:
            self._xlabel = "value"
        if not self._ylabel:
            self._ylabel = "count"
        return self

    def _set_pie(
        self,
        values: Any,
        labels: Sequence[str] | None = None,
    ) -> "Plot":
        if isinstance(values, dict):
            labs, vals = utils.dict_to_xy(values)
            if labels is not None:
                labs = utils.as_str_list(labels)
        else:
            vals = utils.as_float_list(values)
            labs = (
                utils.as_str_list(labels)
                if labels is not None
                else [f"#{i+1}" for i in range(len(vals))]
            )
        # pad labels
        if len(labs) < len(vals):
            labs = labs + [f"#{i+1}" for i in range(len(labs), len(vals))]
        self._series = [
            {
                "kind": "pie",
                "values": vals,
                "labels": labs[: len(vals)],
                "label": "pie",
                "color": None,
            }
        ]
        return self

    # ------------------------------------------------------------------ #
    # render
    # ------------------------------------------------------------------ #

    def _palette_colors(self) -> list[str]:
        theme = get_theme(self._theme_name)
        name = self._palette or theme.get("palette", "default")
        return get_palette(name)

    def _auto_markers(self, n_points: int) -> bool:
        if self._markers is not None:
            return self._markers
        return n_points <= 40

    def render(self) -> str:
        """Build and return SVG (cached until data/style changes)."""
        if self._svg is not None:
            return self._svg

        try:
            self._svg = self._render_unsafe()
        except Exception as exc:
            # never crash the host app — return a visible error chart
            r = SVGRenderer(self.width, self.height, theme=self._theme_name)
            r.begin()
            r.title(self._title or "ezplot")
            r.empty_message(f"Render error: {exc}")
            self._svg = r.finish()
        return self._svg

    def _render_unsafe(self) -> str:
        theme = self._theme_name
        r = SVGRenderer(self.width, self.height, theme=theme)

        # adaptive margins
        if self._tight:
            r.margin.update({"top": 36, "right": 16, "bottom": 40, "left": 48})
        if self._ylabel:
            r.margin["left"] = max(r.margin.get("left", 64), 72)
        if self._horizontal:
            r.margin["left"] = max(r.margin["left"], 100)
        if self._xlabel:
            r.margin["bottom"] = max(r.margin.get("bottom", 56), 60)
        if getattr(self, "_subtitle", ""):
            r.margin["top"] = max(r.margin.get("top", 48), 58)
        if getattr(self, "_footnote", ""):
            r.margin["bottom"] = max(r.margin.get("bottom", 56), 70)
        if self.kind == "bar" or (
            self._series and self._series[0].get("kind") == "bar"
        ):
            cats = (self._series[0].get("categories") or []) if self._series else []
            if len(cats) > 8 or any(len(str(c)) > 10 for c in cats):
                r.margin["bottom"] = max(r.margin["bottom"], 78)
        if self._margin_override:
            r.margin.update(self._margin_override)
        if self._bg_override:
            # temporarily override theme bg for this renderer
            r.theme = dict(r.theme)
            r.theme["bg"] = self._bg_override

        r.begin()
        r.title(self._title)
        if getattr(self, "_subtitle", ""):
            r.subtitle(self._subtitle)

        if not self._series:
            r.empty_message("No data")
            r.xlabel(self._xlabel)
            r.ylabel(self._ylabel)
            if getattr(self, "_footnote", ""):
                r.footnote(self._footnote)
            return r.finish()

        kind = self._series[0].get("kind", self.kind)
        palette = self._palette_colors()

        if kind == "pie":
            return self._render_pie(r, palette)
        if kind == "bar":
            return self._render_bar(r, palette)
        return self._render_xy(r, palette)

    def _render_pie(self, r: SVGRenderer, palette: list[str]) -> str:
        s = self._series[0]
        n = len(s["values"])
        colors = [palette[i % len(palette)] for i in range(n)]
        if self._color and n:
            colors[0] = self._color
        r.pie(s["values"], s["labels"], colors, donut=self._donut)
        r.xlabel(self._xlabel)
        r.ylabel(self._ylabel)
        if getattr(self, "_footnote", ""):
            r.footnote(self._footnote)
        return r.finish()

    def _render_bar(self, r: SVGRenderer, palette: list[str]) -> str:
        cats = list(self._series[0].get("categories") or [])
        n = len(cats)
        all_vals: list[float] = []
        for s in self._series:
            for v in s.get("values") or []:
                if isinstance(v, (int, float)) and math.isfinite(float(v)):
                    all_vals.append(float(v))

        if self._horizontal:
            # value on x
            if self._xlim:
                x0, x1 = self._xlim
            else:
                x0, x1 = utils.data_range(all_vals + [0.0], pad=0.08, include_zero=True)
            y0, y1 = 0.0, float(max(n, 1))
            # draw value axis as x
            r.axes(x0, x1, 0, 1, grid=self._grid, categorical_x=False)
            # hide default y labels by covering with h-bars labels
            colors = (
                [self._color] * n
                if self._color and len(self._series) == 1
                else [palette[i % len(palette)] for i in range(n)]
            )
            vals = self._series[0]["values"]
            r.bars_h(n, vals, x0, x1, colors, cats)
            r.xlabel(self._xlabel)
            r.ylabel(self._ylabel)
            return r.finish()

        if self._ylim:
            y0, y1 = self._ylim
        else:
            y0, y1 = utils.data_range(all_vals + [0.0], pad=0.08, include_zero=True)

        r.axes(
            0,
            max(n, 1),
            y0,
            y1,
            grid=self._grid,
            xlabels=cats,
            categorical_x=True,
        )

        n_groups = len(self._series)
        legend_items: list[tuple[str, str]] = []

        # stacked multi-series
        if getattr(self, "_stacked", False) and n_groups > 1:
            series_vals = []
            colors = []
            for gi, s in enumerate(self._series):
                series_vals.append(s.get("values") or [])
                c = s.get("color") or palette[gi % len(palette)]
                colors.append(c)
                legend_items.append((s["label"], c))
            # recompute y range for stacks
            if self._ylim is None:
                totals = []
                for i in range(n):
                    totals.append(sum(
                        float(sv[i]) for sv in series_vals
                        if i < len(sv) and isinstance(sv[i], (int, float)) and math.isfinite(float(sv[i]))
                    ))
                y0, y1 = utils.data_range(totals + [0.0], pad=0.08, include_zero=True)
                # redraw axes with new range — axes already drawn; for simplicity stack with existing
            r.bars_stacked(max(n, 1), series_vals, y0, y1, colors)
        else:
            for gi, s in enumerate(self._series):
                if n_groups == 1:
                    if self._color:
                        cols = [self._color] * max(n, 1)
                    else:
                        cols = [palette[i % len(palette)] for i in range(max(n, 1))]
                else:
                    c = s.get("color") or palette[gi % len(palette)]
                    cols = [c]
                    legend_items.append((s["label"], c))
                r.bars_v(
                    max(n, 1),
                    s.get("values") or [],
                    y0,
                    y1,
                    cols if cols else ["#3b82f6"],
                    group=gi,
                    n_groups=n_groups,
                    show_values=self._show_values and n_groups == 1,
                )

        # ref lines (value on y)
        for hl in getattr(self, "_hlines", []) or []:
            r.hline(hl["y"], y0, y1, hl.get("color") or "#94a3b8",
                    dashed=hl.get("dashed", True), width=hl.get("width", 1.5))

        if self._legend and legend_items:
            r.legend(legend_items, kind="bar", pos=getattr(self, "_legend_pos", "top-right"))
        r.xlabel(self._xlabel)
        r.ylabel(self._ylabel)
        if getattr(self, "_footnote", ""):
            r.footnote(self._footnote)
        return r.finish()

    def _render_xy(self, r: SVGRenderer, palette: list[str]) -> str:
        all_x: list[float] = []
        all_y: list[float] = []
        prepared: list[dict[str, Any]] = []

        for s in self._series:
            xs = list(s.get("x") or [])
            ys = list(s.get("y") or [])
            if self._sort_x:
                xs, ys = utils.align_xy(xs, ys, drop_nan=False, sort_x=True)
            n = min(len(xs), len(ys))
            xs, ys = xs[:n], ys[:n]
            for x, y in zip(xs, ys):
                if isinstance(x, (int, float)) and math.isfinite(float(x)):
                    all_x.append(float(x))
                if isinstance(y, (int, float)) and math.isfinite(float(y)):
                    all_y.append(float(y))
            prepared.append({**s, "x": xs, "y": ys})

        if not all_x and not all_y:
            r.empty_message("No numeric data")
            return r.finish()

        x0, x1 = self._xlim if self._xlim else utils.data_range(all_x, pad=0.02)
        y0, y1 = self._ylim if self._ylim else utils.data_range(all_y, pad=0.08)

        # categorical x labels if we stored them
        if self._categories and all(
            abs(x - round(x)) < 1e-9 for x in all_x
        ):
            r.axes(
                0,
                max(len(self._categories), 1),
                y0,
                y1,
                grid=self._grid,
                xlabels=self._categories,
                categorical_x=True,
            )
        else:
            r.axes(x0, x1, y0, y1, grid=self._grid)

        legend_items: list[tuple[str, str]] = []
        for i, s in enumerate(prepared):
            c = s.get("color")
            if not c:
                c = self._color if (i == 0 and self._color) else palette[i % len(palette)]
            sk = s.get("kind", self.kind)
            xs, ys = s["x"], s["y"]
            n_pts = sum(
                1
                for x, y in zip(xs, ys)
                if isinstance(x, (int, float))
                and isinstance(y, (int, float))
                and math.isfinite(float(x))
                and math.isfinite(float(y))
            )

            if sk == "area":
                r.area(xs, ys, x0, x1, y0, y1, c)
            elif sk == "scatter":
                r.scatter(xs, ys, x0, x1, y0, y1, c, size=self._size, alpha=self._alpha)
            else:
                r.line(
                    xs,
                    ys,
                    x0,
                    x1,
                    y0,
                    y1,
                    c,
                    width=self._linewidth,
                    markers=self._auto_markers(n_pts),
                    dashed=self._dashed,
                )
            legend_items.append((s["label"], c))

        # reference lines & annotations (data coords)
        for hl in getattr(self, "_hlines", []) or []:
            r.hline(hl["y"], y0, y1, hl.get("color") or "#94a3b8",
                    dashed=hl.get("dashed", True), width=hl.get("width", 1.5))
        for vl in getattr(self, "_vlines", []) or []:
            r.vline(vl["x"], x0, x1, vl.get("color") or "#94a3b8",
                    dashed=vl.get("dashed", True), width=vl.get("width", 1.5))
        for ann in getattr(self, "_annotations", []) or []:
            r.annotate(ann["x"], ann["y"], x0, x1, y0, y1, ann["text"],
                       color=ann.get("color"), anchor=ann.get("anchor") or "start")

        if self._legend and len(prepared) > 1:
            r.legend(
                legend_items,
                kind="scatter" if self.kind == "scatter" else "line",
                pos=getattr(self, "_legend_pos", "top-right"),
            )

        r.xlabel(self._xlabel)
        r.ylabel(self._ylabel)
        if getattr(self, "_footnote", ""):
            r.footnote(self._footnote)
        return r.finish()

    # ------------------------------------------------------------------ #
    # raster render (PNG / JPEG / …)
    # ------------------------------------------------------------------ #

    def _render_raster(self):
        """Build a Canvas (cached)."""
        if self._raster is not None:
            return self._raster
        from .raster import RasterRenderer

        dpi = max(1, int(getattr(self, "_dpi", 1) or 1))
        rw, rh = self.width * dpi, self.height * dpi
        r = RasterRenderer(rw, rh, theme=self._theme_name)
        # scale margins with dpi
        for k in list(r.margin.keys()):
            r.margin[k] = int(r.margin[k] * dpi)
        if self._tight:
            r.margin.update({k: int(v * dpi) for k, v in
                             {"top": 36, "right": 16, "bottom": 40, "left": 48}.items()})
        if self._ylabel:
            r.margin["left"] = max(r.margin["left"], int(72 * dpi))
        if self._horizontal:
            r.margin["left"] = max(r.margin["left"], int(100 * dpi))
        if self._xlabel:
            r.margin["bottom"] = max(r.margin["bottom"], int(60 * dpi))
        if getattr(self, "_subtitle", ""):
            r.margin["top"] = max(r.margin["top"], int(58 * dpi))
        if getattr(self, "_footnote", ""):
            r.margin["bottom"] = max(r.margin["bottom"], int(70 * dpi))
        if self._series and self._series[0].get("kind") == "bar":
            cats = self._series[0].get("categories") or []
            if len(cats) > 8 or any(len(str(c)) > 10 for c in cats):
                r.margin["bottom"] = max(r.margin["bottom"], int(78 * dpi))
        if self._margin_override:
            r.margin.update({k: int(v * dpi) for k, v in self._margin_override.items()})
        if self._bg_override:
            from .raster import parse_color
            r.theme = dict(r.theme)
            r.theme["bg"] = self._bg_override
            r._bg = parse_color(self._bg_override, r._bg)
            r.cv.fill(r._bg)

        r.title(self._title)
        if getattr(self, "_subtitle", "") and hasattr(r, "subtitle"):
            r.subtitle(self._subtitle)
        if not self._series:
            r.empty_message("No data")
            r.xlabel(self._xlabel)
            r.ylabel(self._ylabel)
            self._raster = r.cv
            return self._raster

        kind = self._series[0].get("kind", self.kind)
        palette = self._palette_colors()

        try:
            if kind == "pie":
                self._raster_pie(r, palette)
            elif kind == "bar":
                self._raster_bar(r, palette)
            else:
                self._raster_xy(r, palette)
        except Exception as exc:
            r.empty_message(f"Render error: {exc}")

        r.xlabel(self._xlabel)
        r.ylabel(self._ylabel)
        if getattr(self, "_footnote", "") and hasattr(r, "footnote"):
            r.footnote(self._footnote)
        self._raster = r.cv
        return self._raster

    def _raster_pie(self, r, palette: list[str]) -> None:
        s = self._series[0]
        n = len(s["values"])
        colors = [palette[i % len(palette)] for i in range(n)]
        if self._color and n:
            colors[0] = self._color
        r.pie(s["values"], s["labels"], colors, donut=self._donut)

    def _raster_bar(self, r, palette: list[str]) -> None:
        cats = list(self._series[0].get("categories") or [])
        n = len(cats)
        all_vals: list[float] = []
        for s in self._series:
            for v in s.get("values") or []:
                if isinstance(v, (int, float)) and math.isfinite(float(v)):
                    all_vals.append(float(v))

        if self._horizontal:
            if self._xlim:
                x0, x1 = self._xlim
            else:
                x0, x1 = utils.data_range(all_vals + [0.0], pad=0.08, include_zero=True)
            r.axes(x0, x1, 0, 1, grid=self._grid, categorical_x=False)
            colors = (
                [self._color] * n
                if self._color and len(self._series) == 1
                else [palette[i % len(palette)] for i in range(max(n, 1))]
            )
            r.bars_h(n, self._series[0]["values"], x0, x1, colors or ["#3b82f6"], cats)
            return

        if self._ylim:
            y0, y1 = self._ylim
        else:
            y0, y1 = utils.data_range(all_vals + [0.0], pad=0.08, include_zero=True)
        r.axes(0, max(n, 1), y0, y1, grid=self._grid, xlabels=cats, categorical_x=True)
        n_groups = len(self._series)
        legend_items: list[tuple[str, str]] = []
        if getattr(self, "_stacked", False) and n_groups > 1 and hasattr(r, "bars_stacked"):
            series_vals, colors = [], []
            for gi, s in enumerate(self._series):
                series_vals.append(s.get("values") or [])
                c = s.get("color") or palette[gi % len(palette)]
                colors.append(c)
                legend_items.append((s["label"], c))
            if self._ylim is None:
                totals = []
                for i in range(n):
                    totals.append(sum(
                        float(sv[i]) for sv in series_vals
                        if i < len(sv) and isinstance(sv[i], (int, float)) and math.isfinite(float(sv[i]))
                    ))
                y0, y1 = utils.data_range(totals + [0.0], pad=0.08, include_zero=True)
            r.bars_stacked(max(n, 1), series_vals, y0, y1, colors)
        else:
            for gi, s in enumerate(self._series):
                if n_groups == 1:
                    cols = (
                        [self._color] * max(n, 1)
                        if self._color
                        else [palette[i % len(palette)] for i in range(max(n, 1))]
                    )
                else:
                    c = s.get("color") or palette[gi % len(palette)]
                    cols = [c]
                    legend_items.append((s["label"], c))
                r.bars_v(
                    max(n, 1),
                    s.get("values") or [],
                    y0,
                    y1,
                    cols or ["#3b82f6"],
                    group=gi,
                    n_groups=n_groups,
                    show_values=self._show_values and n_groups == 1,
                )
        for hl in getattr(self, "_hlines", []) or []:
            if hasattr(r, "hline"):
                r.hline(hl["y"], y0, y1, hl.get("color") or "#94a3b8",
                        dashed=hl.get("dashed", True), width=hl.get("width", 1.5))
        if self._legend and legend_items:
            try:
                r.legend(legend_items, kind="bar", pos=getattr(self, "_legend_pos", "top-right"))
            except TypeError:
                r.legend(legend_items, kind="bar")

    def _raster_xy(self, r, palette: list[str]) -> None:
        all_x: list[float] = []
        all_y: list[float] = []
        prepared: list[dict[str, Any]] = []
        for s in self._series:
            xs = list(s.get("x") or [])
            ys = list(s.get("y") or [])
            if self._sort_x:
                xs, ys = utils.align_xy(xs, ys, drop_nan=False, sort_x=True)
            n = min(len(xs), len(ys))
            xs, ys = xs[:n], ys[:n]
            for x, y in zip(xs, ys):
                if isinstance(x, (int, float)) and math.isfinite(float(x)):
                    all_x.append(float(x))
                if isinstance(y, (int, float)) and math.isfinite(float(y)):
                    all_y.append(float(y))
            prepared.append({**s, "x": xs, "y": ys})
        if not all_x and not all_y:
            r.empty_message("No numeric data")
            return
        x0, x1 = self._xlim if self._xlim else utils.data_range(all_x, pad=0.02)
        y0, y1 = self._ylim if self._ylim else utils.data_range(all_y, pad=0.08)
        if self._categories and all(abs(x - round(x)) < 1e-9 for x in all_x):
            r.axes(0, max(len(self._categories), 1), y0, y1, grid=self._grid, xlabels=self._categories, categorical_x=True)
        else:
            r.axes(x0, x1, y0, y1, grid=self._grid)
        legend_items: list[tuple[str, str]] = []
        for i, s in enumerate(prepared):
            c = s.get("color") or (self._color if i == 0 and self._color else palette[i % len(palette)])
            sk = s.get("kind", self.kind)
            xs, ys = s["x"], s["y"]
            n_pts = sum(
                1 for x, y in zip(xs, ys)
                if isinstance(x, (int, float)) and isinstance(y, (int, float))
                and math.isfinite(float(x)) and math.isfinite(float(y))
            )
            if sk == "area":
                r.area_series(xs, ys, x0, x1, y0, y1, c)
            elif sk == "scatter":
                r.scatter_series(xs, ys, x0, x1, y0, y1, c, size=self._size, alpha=self._alpha)
            else:
                r.line_series(xs, ys, x0, x1, y0, y1, c, width=self._linewidth, markers=self._auto_markers(n_pts))
            legend_items.append((s["label"], c))
        for hl in getattr(self, "_hlines", []) or []:
            if hasattr(r, "hline"):
                r.hline(hl["y"], y0, y1, hl.get("color") or "#94a3b8",
                        dashed=hl.get("dashed", True), width=hl.get("width", 1.5))
        for vl in getattr(self, "_vlines", []) or []:
            if hasattr(r, "vline"):
                r.vline(vl["x"], x0, x1, vl.get("color") or "#94a3b8",
                        dashed=vl.get("dashed", True), width=vl.get("width", 1.5))
        for ann in getattr(self, "_annotations", []) or []:
            if hasattr(r, "annotate"):
                r.annotate(ann["x"], ann["y"], x0, x1, y0, y1, ann["text"],
                           color=ann.get("color"), anchor=ann.get("anchor") or "start")
        if self._legend and len(prepared) > 1:
            try:
                r.legend(legend_items, kind="scatter" if self.kind == "scatter" else "line",
                         pos=getattr(self, "_legend_pos", "top-right"))
            except TypeError:
                r.legend(legend_items, kind="scatter" if self.kind == "scatter" else "line")

    # ------------------------------------------------------------------ #
    # output
    # ------------------------------------------------------------------ #

    def save(
        self,
        path: str | os.PathLike = "chart.png",
        *,
        html: bool = False,
        quality: int | None = None,
    ) -> "Plot":
        """
        Save the chart. Format is chosen from the file extension:

            .svg   → vector SVG (default if no extension for legacy)
            .png   → PNG (pure Python, zero deps)
            .jpg / .jpeg → JPEG (needs Pillow)
            .webp  → WebP (needs Pillow)
            .html  → self-contained HTML page

        Examples:
            p.save("out.png")
            p.save("out.jpg")
            p.save("out.svg")
            ez.line([1,2,3], save="chart.png")
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        ext = path.suffix.lower()
        q = int(quality if quality is not None else self._quality)

        if html or ext in {".html", ".htm"}:
            if ext not in {".html", ".htm"}:
                path = path.with_suffix(".html")
            path.write_text(self._as_html(), encoding="utf-8")
            return self

        if ext in _RASTER_EXTS:
            # normalize .jpe → .jpeg path is fine
            cv = self._render_raster()
            # jpeg alias
            if ext == ".jpe":
                path = path.with_suffix(".jpeg")
            cv.save(path, quality=q)
            return self

        # svg (default)
        if not ext:
            path = path.with_suffix(".svg")
        path.write_text(self.render(), encoding="utf-8")
        return self

    def png(self, path: str | os.PathLike = "chart.png") -> "Plot":
        """Save as PNG (zero dependencies)."""
        return self.save(Path(path).with_suffix(".png"))

    def jpg(self, path: str | os.PathLike = "chart.jpg", quality: int = 90) -> "Plot":
        """Save as JPEG (requires Pillow)."""
        return self.save(Path(path).with_suffix(".jpg"), quality=quality)

    def jpeg(self, path: str | os.PathLike = "chart.jpeg", quality: int = 90) -> "Plot":
        return self.jpg(path, quality=quality)

    def svg(self) -> str:
        """Return SVG markup as a string."""
        return self.render()

    def png_bytes(self) -> bytes:
        """Return raw PNG bytes (great for web responses / notebooks)."""
        return self._render_raster().to_png_bytes()

    def image(self):
        """
        Return a PIL Image (if Pillow installed), else raise with a clear message.
        """
        try:
            return self._render_raster().to_pil()
        except ImportError as e:
            raise RuntimeError("Pillow is required for .image() — pip install pillow") from e

    def _as_html(self, svg: str | None = None) -> str:
        svg = svg or self.render()
        bg = get_theme(self._theme_name)["bg"]
        title = utils.escape_xml(self._title or "ezplot")
        return (
            "<!DOCTYPE html>\n<html><head><meta charset='utf-8'>"
            f"<title>{title}</title>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<style>html,body{margin:0;min-height:100%;display:flex;align-items:center;"
            f"justify-content:center;background:{bg};font-family:system-ui,sans-serif;}}"
            "svg{max-width:96vw;height:auto;box-shadow:0 4px 24px rgba(0,0,0,.08);"
            "border-radius:8px;}</style></head><body>\n"
            f"{svg}\n</body></html>"
        )

    def show(self, *, browser: bool | None = None) -> "Plot":
        """
        Display the chart.

        - Jupyter → inline SVG
        - Else → open temp HTML in the default browser
        - browser=False → print a short SVG preview only
        """
        svg = self.render()

        if browser is not True:
            try:
                from IPython.display import display, HTML  # type: ignore

                get_ipython  # type: ignore  # noqa: F821 — only in IPython
                display(HTML(svg))
                return self
            except Exception:
                pass

        if browser is False:
            print(svg[:200] + ("…" if len(svg) > 200 else ""))
            return self

        tmp = tempfile.NamedTemporaryFile(
            prefix="ezplot_", suffix=".html", delete=False, mode="w", encoding="utf-8"
        )
        tmp.write(self._as_html(svg))
        tmp.close()
        try:
            webbrowser.open(Path(tmp.name).as_uri())
        except Exception:
            print(f"ezplot: open this file in a browser → {tmp.name}")
        return self

    def __repr__(self) -> str:
        return f"<ezplot.Plot kind={self.kind!r} series={len(self._series)} title={self._title!r}>"

    def _repr_svg_(self) -> str:
        return self.render()

    def _repr_html_(self) -> str:
        return self.render()

    def _repr_png_(self) -> bytes:
        """Jupyter PNG rich display."""
        try:
            return self.png_bytes()
        except Exception:
            return b""
