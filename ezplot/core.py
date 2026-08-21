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


class _AxisStats:
    """Streaming per-axis aggregates (min/max/positivity/integrality).

    Replaces the old `all_x`/`all_y` full-copy lists in `_prepare_xy` so
    axis-range computation costs O(1) memory instead of O(n) per axis.
    """

    __slots__ = ("count", "lo", "hi", "pos_lo", "pos_hi", "all_int")

    def __init__(self) -> None:
        self.count = 0
        self.lo = math.inf
        self.hi = -math.inf
        self.pos_lo = math.inf   # smallest strictly-positive value
        self.pos_hi = -math.inf  # largest strictly-positive value
        self.all_int = True      # every value is (near-)integral

    def add(self, v: float) -> None:
        self.count += 1
        if v < self.lo:
            self.lo = v
        if v > self.hi:
            self.hi = v
        if v > 0:
            if v < self.pos_lo:
                self.pos_lo = v
            if v > self.pos_hi:
                self.pos_hi = v
        if self.all_int and not abs(v - round(v)) < 1e-9:
            self.all_int = False

    @property
    def has_nonpositive(self) -> bool:
        return self.count > 0 and self.lo <= 0

    def data_range(self, pad: float = 0.05) -> tuple[float, float]:
        """Padded min/max range (mirrors utils.data_range semantics)."""
        if self.count == 0:
            return 0.0, 1.0
        lo, hi = self.lo, self.hi
        if lo == hi:
            d = abs(lo) * 0.1 if lo != 0 else 1.0
            return lo - d, hi + d
        span = hi - lo
        return lo - span * pad, hi + span * pad

    def log_range(self, pad: float = 0.12) -> tuple[float, float]:
        """Positive range for log axes: multiplicative padding (never <= 0)."""
        if self.pos_hi < self.pos_lo:  # no positive values seen
            return 1.0, 10.0
        return self.pos_lo / (1 + pad), self.pos_hi * (1 + pad)


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
        self._hspans: list[dict[str, Any]] = []
        self._vspans: list[dict[str, Any]] = []
        self._margin_override: dict | None = None
        self._yticks: list[float] | None = None
        self._xticks: list[float] | None = None
        self._draw_fn: list[Any] = []
        self._xrot: float | bool = False      # x tick label rotation (degrees or True)
        self._step = False                    # step rendering for lines/areas
        self._trend = False                   # linear trend line overlay
        self._trend_color: str | None = None
        self._trend_dashed = True
        self._trend_label = "trend"
        self._smooth: int | None = None       # moving-average window
        self._yerr: Any = None                # scalar or per-point errors
        self._xerr: Any = None
        self._values_fmt: str | None = None   # bar value label format

        self._series: list[dict[str, Any]] = []
        self._categories: list[str] | None = None
        self._xlim: tuple[float, float] | None = None
        self._ylim: tuple[float, float] | None = None
        self._svg: str | None = None
        self._raster = None  # cached Canvas
        self._x_is_datetime = False

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
            "xticks": "xticks",
            "yticks": "yticks",
            "xrot": "xrot",
            "rotate": "xrot",
            "step": "step",
            "trend": "trend",
            "smooth": "smooth",
            "yerr": "yerr",
            "xerr": "xerr",
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
            elif key == "xticks":
                self.xticks(v)
            elif key == "yticks":
                self.yticks(v)
            elif key == "xrot":
                self.xrot(v)
            elif key == "step":
                self.step(v)
            elif key == "trend":
                self.trend(v)
            elif key == "smooth":
                self.smooth(v)
            elif key == "yerr":
                self.yerr(v)
            elif key == "xerr":
                self.xerr(v)
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

    def values(self, on: bool | str = True, *, fmt: str | None = None) -> "Plot":
        """
        Show numeric labels on bars.

            .values()               # auto-formatted (1.5k, 42, …)
            .values(fmt="{:.1f}")   # custom format string
        """
        if isinstance(on, str):
            self._values_fmt = on
            self._show_values = True
        else:
            self._show_values = bool(on)
        if fmt is not None:
            self._values_fmt = fmt
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

    def xrot(self, degrees: float | bool = 35) -> "Plot":
        """Rotate x tick labels by `degrees` (True = 35°)."""
        if degrees is True:
            self._xrot = 35.0
        elif degrees in (None, False):
            self._xrot = False
        else:
            try:
                self._xrot = float(degrees)
            except (TypeError, ValueError):
                self._xrot = False
        return self._dirty()

    def rotate_xticks(self, degrees: float | bool = 35) -> "Plot":
        """Alias for .xrot()."""
        return self.xrot(degrees)

    def step(self, on: bool = True) -> "Plot":
        """Render line/area as a step chart (value holds until the next x)."""
        self._step = bool(on)
        return self._dirty()

    def trend(self, on: bool = True, *, color: str | None = None,
              dashed: bool = True, label: str = "trend") -> "Plot":
        """Overlay a least-squares linear trend line on line/scatter charts."""
        self._trend = bool(on)
        self._trend_color = color
        self._trend_dashed = bool(dashed)
        self._trend_label = str(label)
        return self._dirty()

    def trendline(self, *args: Any, **kw: Any) -> "Plot":
        """Alias for .trend()."""
        return self.trend(*args, **kw)

    def smooth(self, window: int | None = 3) -> "Plot":
        """Smooth line/area series with a centered moving average."""
        if window is None or window is False:
            self._smooth = None
        else:
            try:
                self._smooth = max(1, int(window))
            except (TypeError, ValueError):
                self._smooth = None
        return self._dirty()

    def yerr(self, err: Any) -> "Plot":
        """Draw vertical error bars: scalar for all points, or a sequence."""
        self._yerr = err
        return self._dirty()

    def xerr(self, err: Any) -> "Plot":
        """Draw horizontal error bars: scalar for all points, or a sequence."""
        self._xerr = err
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

    def annotate(self, x: Any, y: Any, text: str, *,
                 color: str | None = None, anchor: str = "start",
                 size: float = 11) -> "Plot":
        """Add a text label at data coordinates (datetimes allowed)."""
        fx = utils.to_float(x)
        fy = utils.to_float(y)
        if fx is None or fy is None:
            return self._dirty()
        self._annotations.append({
            "x": fx, "y": fy, "text": str(text),
            "color": color, "anchor": anchor, "size": size,
        })
        return self._dirty()

    def hline(self, y: Any, *, color: str = "#94a3b8",
              dashed: bool = True, label: str = "", width: float = 1.5) -> "Plot":
        """Horizontal reference line at y (datetimes allowed)."""
        fy = utils.to_float(y)
        if fy is None:
            return self._dirty()
        self._hlines.append({
            "y": fy, "color": color, "dashed": dashed,
            "label": label, "width": width,
        })
        return self._dirty()

    def axhspan(self, ymin: Any, ymax: Any, *, color: str = "#10b981", alpha: float = 0.25) -> "Plot":
        """Add a horizontal span (rectangle) across the entire x-axis."""
        a, b = utils.to_float(ymin), utils.to_float(ymax)
        if a is None or b is None:
            return self._dirty()
        self._hspans.append({
            "ymin": min(a, b), "ymax": max(a, b),
            "color": color, "alpha": float(alpha),
        })
        return self._dirty()

    def axvspan(self, xmin: Any, xmax: Any, *, color: str = "#10b981", alpha: float = 0.25) -> "Plot":
        """Add a vertical span (rectangle) across the entire y-axis."""
        a, b = utils.to_float(xmin), utils.to_float(xmax)
        if a is None or b is None:
            return self._dirty()
        self._vspans.append({
            "xmin": min(a, b), "xmax": max(a, b),
            "color": color, "alpha": float(alpha),
        })
        return self._dirty()

    def vline(self, x: Any, *, color: str = "#94a3b8",
              dashed: bool = True, label: str = "", width: float = 1.5) -> "Plot":
        """Vertical reference line at x (datetimes allowed)."""
        fx = utils.to_float(x)
        if fx is None:
            return self._dirty()
        self._vlines.append({
            "x": fx, "color": color, "dashed": dashed,
            "label": label, "width": width,
        })
        return self._dirty()

    def xticks(self, ticks: Sequence[Any] | None) -> "Plot":
        if ticks is None:
            self._xticks = None
        else:
            vals = [utils.to_float(t) for t in ticks]
            self._xticks = [v for v in vals if v is not None]
        return self._dirty()

    def yticks(self, ticks: Sequence[Any] | None) -> "Plot":
        if ticks is None:
            self._yticks = None
        else:
            vals = [utils.to_float(t) for t in ticks]
            self._yticks = [v for v in vals if v is not None]
        return self._dirty()

    def draw(self, fn: Any) -> "Plot":
        """
        Add a post-render callback to perform custom low-level drawing over the chart area.
        The callback `fn` receives the renderer (SVGRenderer or RasterRenderer).
        """
        self._draw_fn.append(fn)
        return self._dirty()

    def configure(self, **kw: Any) -> "Plot":
        """Alias for style() — set many options at once."""
        return self.style(**kw)

    def xlim(self, lo: Any, hi: Any) -> "Plot":
        """Set x-axis limits (numbers or datetimes)."""
        try:
            a, b = utils.to_float(lo), utils.to_float(hi)
            if a is not None and b is not None and math.isfinite(a) and math.isfinite(b):
                self._xlim = (min(a, b), max(a, b))
        except (TypeError, ValueError):
            pass
        return self._dirty()

    def ylim(self, lo: Any, hi: Any) -> "Plot":
        """Set y-axis limits (numbers or datetimes)."""
        try:
            a, b = utils.to_float(lo), utils.to_float(hi)
            if a is not None and b is not None and math.isfinite(a) and math.isfinite(b):
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

        if k == "custom":
            self._series.append(
                {
                    "kind": "custom",
                    "x": x,
                    "y": y,
                    "label": lab,
                    "color": color,
                }
            )
        elif k == "box":
            if y is None and x is not None:
                self._set_box(x, labels=[lab] if label else None)
            elif y is not None:
                self._set_box(y, labels=[lab] if label else None)
        elif k == "heat":
            self._set_heat(x if x is not None else y)
        elif k in ("bar", "pie"):
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
        force_multi: bool = False,
    ) -> "Plot":
        """Used by line/scatter/area factories. Supports multi-y + pairs + dicts.

        `force_multi` disambiguates a list-of-lists as parallel y series."""
        self._x_is_datetime = False

        # pandas-like DataFrame as y → named series using column names
        df_cols = utils.dataframe_columns(y)
        if df_cols is not None and y is not None and not isinstance(y, (dict, list, tuple)):
            series_list = [utils.as_float_list_keep_nan(utils.as_list(y[c])) for c in df_cols]
            labs = list(labels) if labels else df_cols
            max_n = max((len(s) for s in series_list), default=0)
            if x is None:
                xs = [float(i) for i in range(max_n)]
            else:
                xs = utils.as_float_list_keep_nan(x)
                self._x_is_datetime = utils.has_datetime(x)
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
                self._x_is_datetime = utils.has_datetime(x)
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

        # pandas-like DataFrame as x (y None) → named series per column
        if y is None:
            df_cols = utils.dataframe_columns(x)
            if df_cols is not None and not isinstance(x, (dict, list, tuple)):
                series_list = [utils.as_float_list_keep_nan(utils.as_list(x[c])) for c in df_cols]
                labs = list(labels) if labels else df_cols
                max_n = max((len(s) for s in series_list), default=0)
                xs = [float(i) for i in range(max_n)]
                self._series = []
                for i, ys in enumerate(series_list):
                    n = min(len(xs), len(ys))
                    self._series.append(
                        {
                            "kind": self.kind,
                            "x": xs[:n],
                            "y": ys[:n],
                            "label": labs[i] if i < len(labs) else f"y{i+1}",
                            "color": None,
                        }
                    )
                return self

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
        multi = force_multi or (
            utils.is_list_of_lists(y) and not utils.is_list_of_pairs(y)
        )
        # when x is given explicitly, a nested y means parallel series
        if x is not None and utils.is_list_of_lists(y):
            multi = True
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
            self._x_is_datetime = utils.has_datetime(x)
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

        cats = utils.as_str_list(categories) if categories is not None else []
        if not cats:
            # no category labels given → synthesize an index so values survive
            if isinstance(values, dict):
                n = max((len(utils.as_list(v)) for v in values.values()), default=0)
            elif utils.is_list_of_lists(values):
                n = max((len(utils.as_list(s)) for s in utils.as_list(values)), default=0)
            else:
                n = len(utils.as_list(values))
            cats = [str(i) for i in range(max(n, 1))]
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

    def _set_box(
        self,
        data: Any,
        labels: Sequence[str] | None = None,
    ) -> "Plot":
        """Box plot data: one list → one box; list of lists / dict → many."""
        self.kind = "box"
        if isinstance(data, dict):
            labs = list(str(k) for k in data.keys())
            boxes = [utils.as_float_list(v) for v in data.values()]
        else:
            items = utils.as_list(data)
            if items and isinstance(items[0], (list, tuple)):
                boxes = [utils.as_float_list(v) for v in items]
            else:
                boxes = [utils.as_float_list(items)]
            labs = (
                [str(l) for l in labels]
                if labels is not None
                else [f"{i + 1}" for i in range(len(boxes))]
            )
        while len(labs) < len(boxes):
            labs.append(f"{len(labs) + 1}")
        self._series = [
            {
                "kind": "box",
                "boxes": boxes,
                "labels": labs[: len(boxes)],
                "label": "box",
                "color": self._color,
            }
        ]
        return self

    def _set_heat(
        self,
        matrix: Any,
        *,
        row_labels: Sequence[str] | None = None,
        col_labels: Sequence[str] | None = None,
        cmap: str = "blues",
        show_values: bool = True,
        colorbar: bool = True,
    ) -> "Plot":
        """Heatmap data from a 2D matrix (list of lists / numpy)."""
        self.kind = "heat"
        mat = utils.as_matrix(matrix)
        if mat is None:
            mat = []
        self._series = [
            {
                "kind": "heat",
                "matrix": mat,
                "row_labels": [str(l) for l in row_labels] if row_labels is not None else None,
                "col_labels": [str(l) for l in col_labels] if col_labels is not None else None,
                "cmap": cmap,
                "show_values": bool(show_values),
                "colorbar": bool(colorbar),
                "label": "heat",
                "color": self._color,
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
        r = SVGRenderer(self.width, self.height, theme=theme, font_scale=self._font_scale)

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
            res = self._render_pie(r, palette)
        elif kind == "bar":
            res = self._render_bar(r, palette)
        elif kind == "custom":
            res = self._render_custom(r, palette)
        elif kind == "box":
            res = self._render_box(r, palette)
        elif kind == "heat":
            res = self._render_heat(r, palette)
        else:
            res = self._render_xy(r, palette)

        # Apply draw callbacks after the primary chart is rendered
        if self._draw_fn:
            for fn in self._draw_fn:
                try:
                    fn(r)
                except Exception:
                    pass
            # update self._svg with the modified renderer output if applicable
            self._svg = r.finish()
            return self._svg
        return res

    def _render_custom(self, r: SVGRenderer, palette: list[str]) -> str:
        # Determine coordinate ranges from x/y values if available
        xs_flat: list[float] = []
        ys_flat: list[float] = []
        for s in self._series:
            x_data = s.get("x")
            y_data = s.get("y")
            if isinstance(x_data, (list, tuple)):
                xs_flat.extend([float(v) for v in x_data if isinstance(v, (int, float)) and math.isfinite(float(v))])
            if isinstance(y_data, (list, tuple)):
                ys_flat.extend([float(v) for v in y_data if isinstance(v, (int, float)) and math.isfinite(float(v))])

        x0, x1 = self._xlim if self._xlim else utils.data_range(xs_flat, pad=0.05)
        y0, y1 = self._ylim if self._ylim else utils.data_range(ys_flat, pad=0.08)

        r.axes(x0, x1, y0, y1, grid=self._grid)

        # A custom chart's rendering is entirely driven by draw callbacks
        # However, we can also support an optional 'draw_fn' as a field on custom series
        for s in self._series:
            draw_callback = s.get("color")  # we can borrow or pass callback through custom mechanisms
            # If a series contains a callable, let's execute it
            for key in ("color", "x", "y"):
                val = s.get(key)
                if callable(val):
                    try:
                        val(r)
                    except Exception:
                        pass

        r.xlabel(self._xlabel)
        r.ylabel(self._ylabel)
        if getattr(self, "_footnote", ""):
            r.footnote(self._footnote)
        return r.finish()

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

    def _render_box(self, r: SVGRenderer, palette: list[str]) -> str:
        s = self._series[0]
        boxes = s.get("boxes") or []
        labels = s.get("labels") or []
        stats = [utils.box_stats(b) for b in boxes]
        all_vals: list[float] = []
        for b in boxes:
            for v in b:
                if isinstance(v, (int, float)) and math.isfinite(float(v)):
                    all_vals.append(float(v))
        if self._ylim:
            y0, y1 = self._ylim
        else:
            y0, y1 = utils.data_range(all_vals + [0.0], pad=0.08, include_zero=True)
        n = max(len(boxes), 1)
        colors = [
            palette[i % len(palette)] for i in range(len(boxes) or 1)
        ]
        if self._horizontal:
            if self._xlim:
                x0, x1 = self._xlim
            else:
                x0, x1 = utils.data_range(all_vals + [0.0], pad=0.08, include_zero=True)
            r.axes(x0, x1, 0, n, grid=self._grid, categorical_x=False, yticks=[])
            r.boxplot(stats, x0, x1, colors, labels=labels, horizontal=True)
        else:
            r.axes(0, n, y0, y1, grid=self._grid, xlabels=labels, categorical_x=True,
                   rotate_x=self._xrot)
            r.boxplot(stats, y0, y1, colors)
        r.xlabel(self._xlabel)
        r.ylabel(self._ylabel)
        if getattr(self, "_footnote", ""):
            r.footnote(self._footnote)
        return r.finish()

    def _render_heat(self, r: SVGRenderer, palette: list[str]) -> str:
        s = self._series[0]
        matrix = s.get("matrix") or []
        rows = len(matrix)
        if rows == 0:
            r.empty_message("No data")
            r.xlabel(self._xlabel)
            r.ylabel(self._ylabel)
            return r.finish()
        cols = max(len(row) for row in matrix)
        if cols == 0:
            r.empty_message("No data")
            r.xlabel(self._xlabel)
            r.ylabel(self._ylabel)
            return r.finish()
        row_labels = s.get("row_labels")
        col_labels = s.get("col_labels")
        show_values = bool(s.get("show_values", True))
        colorbar = bool(s.get("colorbar", True))
        cmap = s.get("cmap") or "blues"
        from .style import get_heatmap
        c0, c1 = get_heatmap(cmap)

        # reserve space for colorbar + labels
        if colorbar:
            r.margin["right"] = max(r.margin["right"], 62)
        if row_labels:
            max_len = max(len(l) for l in row_labels)
            r.margin["left"] = max(r.margin["left"], 16 + max_len * 7)
        if col_labels:
            r.margin["bottom"] = max(r.margin["bottom"], 64)

        finite = [
            v for row in matrix for v in row
            if v is not None and math.isfinite(float(v))
        ]
        vmin = min(finite) if finite else 0.0
        vmax = max(finite) if finite else 1.0
        if vmax == vmin:
            vmax = vmin + 1.0
        cell_colors: list[list[str]] = []
        for row in matrix:
            cell_colors.append([
                utils.interp_color(c0, c1, (float(v) - vmin) / (vmax - vmin))
                if v is not None else r.theme["grid"]
                for v in row
            ])
        r.heatmap(matrix, cell_colors, r.theme["grid"],
                  show_values=show_values, value_fmt=self._values_fmt)
        if colorbar:
            r.heat_colorbar(c0, c1, vmin, vmax)
        # row / column labels
        left, top = r.margin["left"], r.margin["top"]
        cell_h = r.plot_h / rows
        cell_w = r.plot_w / cols
        for i, lab in enumerate(row_labels or []):
            r.draw_text(left - 8, top + (i + 0.5) * cell_h - 4, utils.truncate_label(lab, 12),
                        r.theme["muted"], align="end", raw_coords=True)
        for j, lab in enumerate(col_labels or []):
            r.draw_text(left + (j + 0.5) * cell_w, top + r.plot_h + 14,
                        utils.truncate_label(lab, 10), r.theme["muted"], align="middle", raw_coords=True)
        r.xlabel(self._xlabel)
        r.ylabel(self._ylabel)
        if getattr(self, "_footnote", ""):
            r.footnote(self._footnote)
        return r.finish()

    def _stacked_bar_extents(
        self,
        series: Sequence[dict[str, Any]],
        n: int,
    ) -> tuple[list[float], list[float]]:
        """Per-category positive and negative totals for stacked bars."""
        pos_totals: list[float] = []
        neg_totals: list[float] = []
        for i in range(n):
            pos = 0.0
            neg = 0.0
            for s in series:
                vals = s.get("values") or []
                if i >= len(vals) or not isinstance(vals[i], (int, float)):
                    continue
                fv = float(vals[i])
                if not math.isfinite(fv):
                    continue
                if fv >= 0:
                    pos += fv
                else:
                    neg += fv
            pos_totals.append(pos)
            neg_totals.append(neg)
        return pos_totals, neg_totals

    def _render_bar(self, r: SVGRenderer, palette: list[str]) -> str:
        series = list(self._series)
        cats = list(series[0].get("categories") or [])
        n = len(cats)

        # .sort() → order categories by value (desc), single series or total
        if self._sort_x and n > 1 and series:
            if len(series) == 1:
                vals0 = series[0].get("values") or []
                order = sorted(
                    range(n),
                    key=lambda i: float(vals0[i]) if i < len(vals0)
                    and isinstance(vals0[i], (int, float)) and math.isfinite(float(vals0[i])) else float("-inf"),
                    reverse=True,
                )
            else:
                def _total(i: int) -> float:
                    tot = 0.0
                    for s in series:
                        vals = s.get("values") or []
                        if i < len(vals) and isinstance(vals[i], (int, float)) and math.isfinite(float(vals[i])):
                            tot += float(vals[i])
                    return tot

                order = sorted(range(n), key=_total, reverse=True)
            cats = [cats[i] for i in order]
            for s in series:
                vals = s.get("values") or []
                s["values"] = [vals[i] if i < len(vals) else 0.0 for i in order]
            series[0]["categories"] = cats

        all_vals: list[float] = []
        for s in series:
            for v in s.get("values") or []:
                if isinstance(v, (int, float)) and math.isfinite(float(v)):
                    all_vals.append(float(v))

        n_groups = len(series)
        stacked = bool(getattr(self, "_stacked", False)) and n_groups > 1

        if self._horizontal:
            # value mapped on x; category axis has no numeric labels
            if self._xlim:
                x0, x1 = self._xlim
            else:
                x0, x1 = utils.bar_range(all_vals)
            r.axes(x0, x1, 0, max(n, 1), grid=self._grid, categorical_x=False, yticks=[],
                   yaxis_at=0.0 if x0 <= 0 <= x1 else None)
            # spans swap meaning for horizontal bars: value band is vertical,
            # category band is horizontal
            for hs in getattr(self, "_hspans", []) or []:
                r.vspan(hs["ymin"], hs["ymax"], x0, x1, hs["color"], hs["alpha"])
            for vs in getattr(self, "_vspans", []) or []:
                r.hspan(vs["xmin"], vs["xmax"], 0, max(n, 1), vs["color"], vs["alpha"])
            s0 = series[0]
            single = s0.get("color") or self._color
            colors = (
                [single] * n
                if single and n_groups == 1
                else [palette[i % len(palette)] for i in range(max(n, 1))]
            )
            r.bars_h(
                max(n, 1),
                s0.get("values") or [],
                x0, x1,
                colors or ["#3b82f6"],
                cats,
                show_values=self._show_values,
                value_fmt=self._values_fmt,
            )
            # ref lines: hline draws across values (vertical), vline across cats
            for hl in getattr(self, "_hlines", []) or []:
                r.vline(hl["y"], x0, x1, hl.get("color") or "#94a3b8",
                        dashed=hl.get("dashed", True), width=hl.get("width", 1.5))
            for vl in getattr(self, "_vlines", []) or []:
                r.hline(vl["x"], 0, max(n, 1), vl.get("color") or "#94a3b8",
                        dashed=vl.get("dashed", True), width=vl.get("width", 1.5))
            r.xlabel(self._xlabel)
            r.ylabel(self._ylabel)
            if getattr(self, "_footnote", ""):
                r.footnote(self._footnote)
            return r.finish()

        # decide y range *before* drawing axes (stacked totals differ from raw vals)
        if self._ylim:
            y0, y1 = self._ylim
        elif stacked:
            pos_totals, neg_totals = self._stacked_bar_extents(series, n)
            y0, y1 = utils.bar_range(pos_totals + neg_totals)
        else:
            y0, y1 = utils.bar_range(all_vals)

        r.axes(
            0,
            max(n, 1),
            y0,
            y1,
            grid=self._grid,
            xlabels=cats,
            categorical_x=True,
            rotate_x=self._xrot,
            xaxis_at=0.0 if y0 <= 0 <= y1 else None,
        )
        # Render background highlight spans
        for hs in getattr(self, "_hspans", []) or []:
            r.hspan(hs["ymin"], hs["ymax"], y0, y1, hs["color"], hs["alpha"])
        for vs in getattr(self, "_vspans", []) or []:
            r.vspan(vs["xmin"], vs["xmax"], 0, max(n, 1), vs["color"], vs["alpha"])

        legend_items: list[tuple[str, str]] = []

        # stacked multi-series
        if stacked:
            series_vals = []
            colors = []
            for gi, s in enumerate(series):
                series_vals.append(s.get("values") or [])
                c = s.get("color") or palette[gi % len(palette)]
                colors.append(c)
                legend_items.append((s["label"], c))
            r.bars_stacked(max(n, 1), series_vals, y0, y1, colors)
        else:
            for gi, s in enumerate(series):
                if n_groups == 1:
                    single = s.get("color") or self._color
                    if single:
                        cols = [single] * max(n, 1)
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
                    value_fmt=self._values_fmt,
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

    def _prepare_xy(
        self,
    ) -> tuple[list[dict[str, Any]], "_AxisStats", "_AxisStats", bool, bool]:
        """Shared SVG/raster prep: sorting, smoothing, error bars, log detection.

        Axis extents are accumulated as streaming `_AxisStats` (not full
        copies of the data), and series lists are only copied when they
        actually need to be transformed — keeping prep memory near O(1)
        for large inputs.
        """
        prepared: list[dict[str, Any]] = []
        xstat = _AxisStats()
        ystat = _AxisStats()
        log_x = bool(getattr(self, "_logx", False))
        log_y = bool(getattr(self, "_logy", False))
        # locals for the per-point hot loops below
        isfinite = math.isfinite
        xadd = xstat.add
        yadd = ystat.add

        for s in self._series:
            xs = s.get("x") or []
            ys = s.get("y") or []
            if not isinstance(xs, (list, tuple)):
                xs = list(xs)
            if not isinstance(ys, (list, tuple)):
                ys = list(ys)
            if self._sort_x:
                xs, ys = utils.align_xy(xs, ys, drop_nan=False, sort_x=True)
            n = min(len(xs), len(ys))
            if len(xs) > n:
                xs = xs[:n]
            if len(ys) > n:
                ys = ys[:n]
            if getattr(self, "_smooth", None):
                ys = utils.moving_average(ys, int(self._smooth))

            # error bars: scalar → every series; flat seq → first; nested → per series
            idx = len(prepared)
            yerr, xerr = s.get("yerr"), s.get("xerr")
            for key, store in (("_yerr", "yerr"), ("_xerr", "xerr")):
                val = getattr(self, key, None)
                if val is None:
                    continue
                if isinstance(val, (int, float)):
                    if store == "yerr":
                        yerr = val
                    else:
                        xerr = val
                else:
                    seq = utils.as_list(val)
                    if seq and isinstance(seq[0], (list, tuple)):
                        if idx < len(seq):
                            if store == "yerr":
                                yerr = seq[idx]
                            else:
                                xerr = seq[idx]
                    elif idx == 0:
                        if store == "yerr":
                            yerr = seq
                        else:
                            xerr = seq

            # per-point loops — `type() is` fast paths since coercion already
            # produced plain floats (nan for gaps)
            for x in xs:
                if type(x) is float:
                    if isfinite(x):
                        xadd(x)
                elif type(x) is int:
                    xadd(float(x))
                elif isinstance(x, (int, float)) and isfinite(float(x)):
                    xadd(float(x))
            for y in ys:
                if type(y) is float:
                    if isfinite(y):
                        yadd(y)
                elif type(y) is int:
                    yadd(float(y))
                elif isinstance(y, (int, float)) and isfinite(float(y)):
                    yadd(float(y))
            n_pts = 0
            for x, y in zip(xs, ys):
                if type(x) is float and type(y) is float:
                    if isfinite(x) and isfinite(y):
                        n_pts += 1
                elif (
                    isinstance(x, (int, float))
                    and isinstance(y, (int, float))
                    and isfinite(float(x))
                    and isfinite(float(y))
                ):
                    n_pts += 1
            prepared.append({**s, "x": xs, "y": ys, "yerr": yerr, "xerr": xerr, "n": n_pts})

        # log axes need strictly positive data; fall back to linear otherwise
        if log_x and xstat.has_nonpositive:
            log_x = False
        if log_y and ystat.has_nonpositive:
            log_y = False
        return prepared, xstat, ystat, log_x, log_y

    def _log_range(self, values: list[float], pad: float = 0.12) -> tuple[float, float]:
        """Positive range for log axes: multiplicative padding (never ≤ 0)."""
        pos = sorted(v for v in values if v > 0)
        if not pos:
            return 1.0, 10.0
        if pos[0] == pos[-1]:
            return pos[0] / (1 + pad), pos[-1] * (1 + pad)
        return pos[0] / (1 + pad), pos[-1] * (1 + pad)

    def _render_xy(self, r: SVGRenderer, palette: list[str]) -> str:
        prepared, xstat, ystat, log_x, log_y = self._prepare_xy()

        if xstat.count == 0 and ystat.count == 0:
            r.empty_message("No numeric data")
            return r.finish()

        x0, x1 = self._xlim if self._xlim else (
            xstat.log_range() if log_x else xstat.data_range(pad=0.02)
        )
        y0, y1 = self._ylim if self._ylim else (
            ystat.log_range() if log_y else ystat.data_range(pad=0.08)
        )

        # categorical x labels if we stored them — series and axis must share
        # the same 0..n mapping so points land exactly on the tick marks
        if self._categories and xstat.all_int:
            x0, x1 = 0.0, float(max(len(self._categories), 1))
            r.axes(
                x0,
                x1,
                y0,
                y1,
                grid=self._grid,
                xlabels=self._categories,
                categorical_x=True,
                categorical_center=False,  # line/scatter points sit on boundaries
                rotate_x=self._xrot,
                log_y=log_y,
                datetime_x=self._x_is_datetime,
            )
        else:
            r.axes(
                x0, x1, y0, y1,
                grid=self._grid,
                rotate_x=self._xrot,
                log_x=log_x,
                log_y=log_y,
                datetime_x=self._x_is_datetime,
                xticks=self._xticks,
                yticks=self._yticks,
            )

        # Render background highlight spans
        for hs in getattr(self, "_hspans", []) or []:
            r.hspan(hs["ymin"], hs["ymax"], y0, y1, hs["color"], hs["alpha"])
        for vs in getattr(self, "_vspans", []) or []:
            r.vspan(vs["xmin"], vs["xmax"], x0, x1, vs["color"], vs["alpha"])

        legend_items: list[tuple[str, str]] = []
        cap = (x1 - x0) * 0.01 if x1 != x0 else 0.5
        for i, s in enumerate(prepared):
            c = s.get("color")
            if not c:
                c = self._color if (i == 0 and self._color) else palette[i % len(palette)]
            sk = s.get("kind", self.kind)
            xs, ys = s["x"], s["y"]
            n_pts = s.get("n", 0)

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
                    step=self._step,
                )
            # error bars (data coords, so they track log/zoom automatically)
            self._draw_err(r, xs, ys, s.get("yerr"), cap, c, vertical=True)
            self._draw_err(r, xs, ys, s.get("xerr"), cap, c, vertical=False)
            legend_items.append((s["label"], c))

        # trend line overlay
        if self._trend and prepared:
            fit = utils.linear_regression(prepared[0]["x"], prepared[0]["y"])
            if fit is not None:
                slope, intercept, _r2 = fit
                tcol = self._trend_color or (
                    palette[1 % len(palette)] if len(palette) > 1 else palette[0]
                )
                r.line(
                    [x0, x1],
                    [intercept + slope * x0, intercept + slope * x1],
                    x0, x1, y0, y1,
                    tcol,
                    width=2,
                    markers=False,
                    dashed=self._trend_dashed,
                )
                legend_items.append((self._trend_label, tcol))

        # reference lines & annotations (data coords)
        for hl in getattr(self, "_hlines", []) or []:
            r.hline(hl["y"], y0, y1, hl.get("color") or "#94a3b8",
                    dashed=hl.get("dashed", True), width=hl.get("width", 1.5))
        for vl in getattr(self, "_vlines", []) or []:
            r.vline(vl["x"], x0, x1, vl.get("color") or "#94a3b8",
                    dashed=vl.get("dashed", True), width=vl.get("width", 1.5))
        for ann in getattr(self, "_annotations", []) or []:
            r.annotate(ann["x"], ann["y"], x0, x1, y0, y1, ann["text"],
                       color=ann.get("color"), anchor=ann.get("anchor") or "start",
                       size=ann.get("size", 11))

        if self._legend and len(legend_items) > 1:
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

    def _draw_err(
        self,
        r: Any,
        xs: list[float],
        ys: list[float],
        err: Any,
        cap: float,
        color: str,
        *,
        vertical: bool,
    ) -> None:
        """Draw error bars with caps using the unified primitive API."""
        if err is None:
            return
        if isinstance(err, (list, tuple)):
            pairs = zip(xs, ys, err)
        else:
            pairs = ((x, y, err) for x, y in zip(xs, ys))
        for x, y, e in pairs:
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                continue
            if not math.isfinite(float(x)) or not math.isfinite(float(y)):
                continue
            f = utils.to_float(e)
            if f is None or f < 0 or not math.isfinite(f):
                continue
            if vertical:
                r.draw_line(x, y - f, x, y + f, color, width=1.5)
                r.draw_line(x - cap, y - f, x + cap, y - f, color, width=1.5)
                r.draw_line(x - cap, y + f, x + cap, y + f, color, width=1.5)
            else:
                r.draw_line(x - f, y, x + f, y, color, width=1.5)
                r.draw_line(x - f, y - cap, x - f, y + cap, color, width=1.5)
                r.draw_line(x + f, y - cap, x + f, y + cap, color, width=1.5)

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
        r = RasterRenderer(rw, rh, theme=self._theme_name, font_scale=self._font_scale)
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
            elif kind == "custom":
                self._raster_custom(r, palette)
            elif kind == "box":
                self._raster_box(r, palette)
            elif kind == "heat":
                self._raster_heat(r, palette)
            else:
                self._raster_xy(r, palette)
        except Exception as exc:
            r.empty_message(f"Render error: {exc}")

        # Apply draw callbacks after the primary chart is rendered
        if self._draw_fn:
            for fn in self._draw_fn:
                try:
                    fn(r)
                except Exception:
                    pass

        r.xlabel(self._xlabel)
        r.ylabel(self._ylabel)
        if getattr(self, "_footnote", "") and hasattr(r, "footnote"):
            r.footnote(self._footnote)
        self._raster = r.cv
        return self._raster

    def _raster_custom(self, r, palette: list[str]) -> None:
        # Determine coordinate ranges from x/y values if available
        xs_flat: list[float] = []
        ys_flat: list[float] = []
        for s in self._series:
            x_data = s.get("x")
            y_data = s.get("y")
            if isinstance(x_data, (list, tuple)):
                xs_flat.extend([float(v) for v in x_data if isinstance(v, (int, float)) and math.isfinite(float(v))])
            if isinstance(y_data, (list, tuple)):
                ys_flat.extend([float(v) for v in y_data if isinstance(v, (int, float)) and math.isfinite(float(v))])

        x0, x1 = self._xlim if self._xlim else utils.data_range(xs_flat, pad=0.05)
        y0, y1 = self._ylim if self._ylim else utils.data_range(ys_flat, pad=0.08)

        r.axes(x0, x1, y0, y1, grid=self._grid)

        # A custom chart's rendering is entirely driven by draw callbacks
        for s in self._series:
            for key in ("color", "x", "y"):
                val = s.get(key)
                if callable(val):
                    try:
                        val(r)
                    except Exception:
                        pass

    def _raster_pie(self, r, palette: list[str]) -> None:
        s = self._series[0]
        n = len(s["values"])
        colors = [palette[i % len(palette)] for i in range(n)]
        if self._color and n:
            colors[0] = self._color
        r.pie(s["values"], s["labels"], colors, donut=self._donut)

    def _raster_box(self, r, palette: list[str]) -> None:
        s = self._series[0]
        boxes = s.get("boxes") or []
        labels = s.get("labels") or []
        stats = [utils.box_stats(b) for b in boxes]
        all_vals: list[float] = []
        for b in boxes:
            for v in b:
                if isinstance(v, (int, float)) and math.isfinite(float(v)):
                    all_vals.append(float(v))
        n = max(len(boxes), 1)
        colors = [palette[i % len(palette)] for i in range(len(boxes) or 1)]
        if self._horizontal:
            if self._xlim:
                x0, x1 = self._xlim
            else:
                x0, x1 = utils.data_range(all_vals + [0.0], pad=0.08, include_zero=True)
            r.axes(x0, x1, 0, n, grid=self._grid, categorical_x=False, yticks=[])
            r.boxplot(stats, x0, x1, colors, labels=labels, horizontal=True)
        else:
            if self._ylim:
                y0, y1 = self._ylim
            else:
                y0, y1 = utils.data_range(all_vals + [0.0], pad=0.08, include_zero=True)
            r.axes(0, n, y0, y1, grid=self._grid, xlabels=labels, categorical_x=True,
                   rotate_x=self._xrot)
            r.boxplot(stats, y0, y1, colors)

    def _raster_heat(self, r, palette: list[str]) -> None:
        s = self._series[0]
        matrix = s.get("matrix") or []
        rows = len(matrix)
        if rows == 0:
            r.empty_message("No data")
            return
        cols = max(len(row) for row in matrix)
        if cols == 0:
            r.empty_message("No data")
            return
        row_labels = s.get("row_labels")
        col_labels = s.get("col_labels")
        show_values = bool(s.get("show_values", True))
        colorbar = bool(s.get("colorbar", True))
        cmap = s.get("cmap") or "blues"
        from .style import get_heatmap
        c0, c1 = get_heatmap(cmap)

        if colorbar:
            r.margin["right"] = max(r.margin["right"], 62)
        if row_labels:
            r.margin["left"] = max(r.margin["left"], 16 + max(len(l) for l in row_labels) * 6)
        if col_labels:
            r.margin["bottom"] = max(r.margin["bottom"], 64)
        r._sync_geom()

        finite = [
            v for row in matrix for v in row
            if v is not None and math.isfinite(float(v))
        ]
        vmin = min(finite) if finite else 0.0
        vmax = max(finite) if finite else 1.0
        if vmax == vmin:
            vmax = vmin + 1.0
        cell_colors: list[list[str]] = []
        for row in matrix:
            cell_colors.append([
                utils.interp_color(c0, c1, (float(v) - vmin) / (vmax - vmin))
                if v is not None else r.theme["grid"]
                for v in row
            ])
        r.heatmap(matrix, cell_colors, r.theme["grid"],
                  show_values=show_values, value_fmt=self._values_fmt)
        if colorbar:
            r.heat_colorbar(c0, c1, vmin, vmax)
        left, top = r._ml, r._mt
        cell_h = r._ph / rows
        cell_w = r._pw / cols
        for i, lab in enumerate(row_labels or []):
            r.draw_text(left - 8, top + (i + 0.5) * cell_h - 4,
                        utils.truncate_label(lab, 12), r.theme["muted"],
                        align="end", raw_coords=True)
        for j, lab in enumerate(col_labels or []):
            r.draw_text(left + (j + 0.5) * cell_w, top + r._ph + 14,
                        utils.truncate_label(lab, 10), r.theme["muted"],
                        align="center", raw_coords=True)

    def _raster_bar(self, r, palette: list[str]) -> None:
        series = list(self._series)
        cats = list(series[0].get("categories") or [])
        n = len(cats)

        # .sort() → order categories by value (desc), single series or total
        if self._sort_x and n > 1 and series:
            if len(series) == 1:
                vals0 = series[0].get("values") or []
                order = sorted(
                    range(n),
                    key=lambda i: float(vals0[i]) if i < len(vals0)
                    and isinstance(vals0[i], (int, float)) and math.isfinite(float(vals0[i])) else float("-inf"),
                    reverse=True,
                )
            else:
                def _total(i: int) -> float:
                    tot = 0.0
                    for s in series:
                        vals = s.get("values") or []
                        if i < len(vals) and isinstance(vals[i], (int, float)) and math.isfinite(float(vals[i])):
                            tot += float(vals[i])
                    return tot

                order = sorted(range(n), key=_total, reverse=True)
            cats = [cats[i] for i in order]
            for s in series:
                vals = s.get("values") or []
                s["values"] = [vals[i] if i < len(vals) else 0.0 for i in order]
            series[0]["categories"] = cats

        all_vals: list[float] = []
        for s in series:
            for v in s.get("values") or []:
                if isinstance(v, (int, float)) and math.isfinite(float(v)):
                    all_vals.append(float(v))

        n_groups = len(series)
        stacked = bool(getattr(self, "_stacked", False)) and n_groups > 1

        if self._horizontal:
            if self._xlim:
                x0, x1 = self._xlim
            else:
                x0, x1 = utils.bar_range(all_vals)
            r.axes(x0, x1, 0, max(n, 1), grid=self._grid, categorical_x=False, yticks=[],
                   yaxis_at=0.0 if x0 <= 0 <= x1 else None)

            # spans swap meaning for horizontal bars
            for hs in getattr(self, "_hspans", []) or []:
                if hasattr(r, "vspan"):
                    r.vspan(hs["ymin"], hs["ymax"], x0, x1, hs["color"], hs["alpha"])
            for vs in getattr(self, "_vspans", []) or []:
                if hasattr(r, "hspan"):
                    r.hspan(vs["xmin"], vs["xmax"], 0, max(n, 1), vs["color"], vs["alpha"])

            s0 = series[0]
            single = s0.get("color") or self._color
            colors = (
                [single] * n
                if single and n_groups == 1
                else [palette[i % len(palette)] for i in range(max(n, 1))]
            )
            r.bars_h(
                max(n, 1), s0.get("values") or [], x0, x1,
                colors or ["#3b82f6"], cats,
                show_values=self._show_values, value_fmt=self._values_fmt,
            )
            for hl in getattr(self, "_hlines", []) or []:
                if hasattr(r, "vline"):
                    r.vline(hl["y"], x0, x1, hl.get("color") or "#94a3b8",
                            dashed=hl.get("dashed", True), width=hl.get("width", 1.5))
            for vl in getattr(self, "_vlines", []) or []:
                if hasattr(r, "hline"):
                    r.hline(vl["x"], 0, max(n, 1), vl.get("color") or "#94a3b8",
                            dashed=vl.get("dashed", True), width=vl.get("width", 1.5))
            return

        # decide y range *before* drawing axes
        if self._ylim:
            y0, y1 = self._ylim
        elif stacked:
            pos_totals, neg_totals = self._stacked_bar_extents(series, n)
            y0, y1 = utils.bar_range(pos_totals + neg_totals)
        else:
            y0, y1 = utils.bar_range(all_vals)
        r.axes(0, max(n, 1), y0, y1, grid=self._grid, xlabels=cats, categorical_x=True,
               rotate_x=self._xrot,
               xaxis_at=0.0 if y0 <= 0 <= y1 else None)

        # Render background highlight spans
        for hs in getattr(self, "_hspans", []) or []:
            if hasattr(r, "hspan"):
                r.hspan(hs["ymin"], hs["ymax"], y0, y1, hs["color"], hs["alpha"])
        for vs in getattr(self, "_vspans", []) or []:
            if hasattr(r, "vspan"):
                r.vspan(vs["xmin"], vs["xmax"], 0, max(n, 1), vs["color"], vs["alpha"])

        legend_items: list[tuple[str, str]] = []
        if stacked and hasattr(r, "bars_stacked"):
            series_vals, colors = [], []
            for gi, s in enumerate(series):
                series_vals.append(s.get("values") or [])
                c = s.get("color") or palette[gi % len(palette)]
                colors.append(c)
                legend_items.append((s["label"], c))
            r.bars_stacked(max(n, 1), series_vals, y0, y1, colors)
        else:
            for gi, s in enumerate(series):
                if n_groups == 1:
                    single = s.get("color") or self._color
                    cols = (
                        [single] * max(n, 1)
                        if single
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
                    value_fmt=self._values_fmt,
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
        prepared, xstat, ystat, log_x, log_y = self._prepare_xy()
        if xstat.count == 0 and ystat.count == 0:
            r.empty_message("No numeric data")
            return
        x0, x1 = self._xlim if self._xlim else (
            xstat.log_range() if log_x else xstat.data_range(pad=0.02)
        )
        y0, y1 = self._ylim if self._ylim else (
            ystat.log_range() if log_y else ystat.data_range(pad=0.08)
        )
        if self._categories and xstat.all_int:
            x0, x1 = 0.0, float(max(len(self._categories), 1))
            r.axes(x0, x1, y0, y1, grid=self._grid,
                   xlabels=self._categories, categorical_x=True,
                   categorical_center=False,  # line/scatter points sit on boundaries
                   rotate_x=self._xrot, log_y=log_y, datetime_x=self._x_is_datetime)
        else:
            r.axes(x0, x1, y0, y1, grid=self._grid,
                   rotate_x=self._xrot, log_x=log_x, log_y=log_y,
                   datetime_x=self._x_is_datetime,
                   xticks=self._xticks, yticks=self._yticks)

        # Render background highlight spans
        for hs in getattr(self, "_hspans", []) or []:
            if hasattr(r, "hspan"):
                r.hspan(hs["ymin"], hs["ymax"], y0, y1, hs["color"], hs["alpha"])
        for vs in getattr(self, "_vspans", []) or []:
            if hasattr(r, "vspan"):
                r.vspan(vs["xmin"], vs["xmax"], x0, x1, vs["color"], vs["alpha"])

        legend_items: list[tuple[str, str]] = []
        cap = (x1 - x0) * 0.01 if x1 != x0 else 0.5
        for i, s in enumerate(prepared):
            c = s.get("color") or (self._color if i == 0 and self._color else palette[i % len(palette)])
            sk = s.get("kind", self.kind)
            xs, ys = s["x"], s["y"]
            n_pts = s.get("n", 0)
            if sk == "area":
                r.area_series(xs, ys, x0, x1, y0, y1, c)
            elif sk == "scatter":
                r.scatter_series(xs, ys, x0, x1, y0, y1, c, size=self._size, alpha=self._alpha)
            else:
                r.line_series(
                    xs, ys, x0, x1, y0, y1, c,
                    width=self._linewidth,
                    markers=self._auto_markers(n_pts),
                    dashed=self._dashed,
                    step=self._step,
                )
            self._draw_err(r, xs, ys, s.get("yerr"), cap, c, vertical=True)
            self._draw_err(r, xs, ys, s.get("xerr"), cap, c, vertical=False)
            legend_items.append((s["label"], c))

        # trend line overlay
        if self._trend and prepared:
            fit = utils.linear_regression(prepared[0]["x"], prepared[0]["y"])
            if fit is not None:
                slope, intercept, _r2 = fit
                tcol = self._trend_color or (
                    palette[1 % len(palette)] if len(palette) > 1 else palette[0]
                )
                r.line_series(
                    [x0, x1],
                    [intercept + slope * x0, intercept + slope * x1],
                    x0, x1, y0, y1,
                    tcol, width=2, markers=False, dashed=self._trend_dashed,
                )
                legend_items.append((self._trend_label, tcol))

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
                           color=ann.get("color"), anchor=ann.get("anchor") or "start",
                           size=ann.get("size", 11))
        if self._legend and len(legend_items) > 1:
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
