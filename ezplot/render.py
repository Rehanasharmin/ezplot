"""Pure-Python SVG renderer — fast, zero dependencies, multi-chart safe."""

from __future__ import annotations

import math
from typing import Sequence

from . import utils
from .style import get_theme


def svg_color_alpha(color: str | Sequence[int] | Sequence[float] | None, opacity: float = 1.0) -> tuple[str, float]:
    """Resolve CSS color string and opacity for SVG, preserving CSS named/hex colors."""
    if color is None:
        return "none", opacity
    if not isinstance(color, str):
        from .raster import parse_color_alpha
        rgb, parsed_a = parse_color_alpha(color)
        return f"rgb({rgb[0]},{rgb[1]},{rgb[2]})", parsed_a * opacity

    s = color.strip().lower()
    if s.startswith("rgba"):
        from .raster import parse_color_alpha
        rgb, parsed_a = parse_color_alpha(s)
        return f"rgb({rgb[0]},{rgb[1]},{rgb[2]})", parsed_a * opacity
    elif s.startswith("#") and len(s) in (5, 9):
        from .raster import parse_color_alpha
        rgb, parsed_a = parse_color_alpha(s)
        return f"rgb({rgb[0]},{rgb[1]},{rgb[2]})", parsed_a * opacity

    return color, opacity


class SVGRenderer:
    """Draw chart series into an SVG string."""

    def __init__(
        self,
        width: int = 720,
        height: int = 420,
        theme: str | None = None,
        margin: dict | None = None,
        font_scale: float = 1.0,
    ):
        self.width = max(120, int(width))
        self.height = max(100, int(height))
        self.theme = get_theme(theme)
        self.margin = dict(margin or {"top": 48, "right": 28, "bottom": 56, "left": 64})
        self.font_scale = font_scale
        self._parts: list[str] = []
        self._defs: list[str] = []
        self._clip_id = utils.unique_id("c")
        self._grad_i = 0
        self.x0 = 0.0
        self.x1 = 1.0
        self.y0 = 0.0
        self.y1 = 1.0
        self._logx = False
        self._logy = False

    # --- geometry ---------------------------------------------------------

    @property
    def plot_w(self) -> float:
        return max(10.0, self.width - self.margin["left"] - self.margin["right"])

    @property
    def plot_h(self) -> float:
        return max(10.0, self.height - self.margin["top"] - self.margin["bottom"])

    def _sx(self, x: float, x0: float, x1: float) -> float:
        if not math.isfinite(x):
            return self.margin["left"]
        if self._logx:
            if x <= 0 or x0 <= 0 or x1 <= 0 or x1 == x0:
                return self.margin["left"] + self.plot_w / 2
            return self.margin["left"] + (math.log10(x) - math.log10(x0)) / (math.log10(x1) - math.log10(x0)) * self.plot_w
        if x1 == x0 or not math.isfinite(x0) or not math.isfinite(x1):
            return self.margin["left"] + self.plot_w / 2
        return self.margin["left"] + (x - x0) / (x1 - x0) * self.plot_w

    def _sy(self, y: float, y0: float, y1: float) -> float:
        if not math.isfinite(y):
            return self.margin["top"] + self.plot_h / 2
        if self._logy:
            if y <= 0 or y0 <= 0 or y1 <= 0 or y1 == y0:
                return self.margin["top"] + self.plot_h / 2
            return self.margin["top"] + (1 - (math.log10(y) - math.log10(y0)) / (math.log10(y1) - math.log10(y0))) * self.plot_h
        if y1 == y0 or not math.isfinite(y0) or not math.isfinite(y1):
            return self.margin["top"] + self.plot_h / 2
        return self.margin["top"] + (1 - (y - y0) / (y1 - y0)) * self.plot_h

    # --- public draw API --------------------------------------------------

    def begin(self) -> None:
        t = self.theme
        self._parts = []
        self._defs = [
            f'<clipPath id="{self._clip_id}">'
            f'<rect x="{self.margin["left"]}" y="{self.margin["top"]}" '
            f'width="{self.plot_w}" height="{self.plot_h}"/>'
            f"</clipPath>"
        ]
        self._parts.append(f'<rect width="100%" height="100%" fill="{t["bg"]}"/>')

    def empty_message(self, msg: str = "No data") -> None:
        t = self.theme
        sz = 14 * self.font_scale
        self._parts.append(
            f'<text x="{self.width/2}" y="{self.height/2}" text-anchor="middle" '
            f'font-family="{t["font"]}" font-size="{sz:.1f}" fill="{t["muted"]}">'
            f"{utils.escape_xml(msg)}</text>"
        )

    def title(self, text: str) -> None:
        if not text:
            return
        t = self.theme
        sz = 16 * self.font_scale
        self._parts.append(
            f'<text x="{self.width / 2}" y="28" text-anchor="middle" '
            f'font-family="{t["font"]}" font-size="{sz:.1f}" font-weight="600" '
            f'fill="{t["title"]}">{utils.escape_xml(text)}</text>'
        )

    def xlabel(self, text: str) -> None:
        if not text:
            return
        t = self.theme
        y = self.height - 12
        sz = 12 * self.font_scale
        self._parts.append(
            f'<text x="{self.margin["left"] + self.plot_w / 2}" y="{y}" '
            f'text-anchor="middle" font-family="{t["font"]}" font-size="{sz:.1f}" '
            f'fill="{t["muted"]}">{utils.escape_xml(text)}</text>'
        )

    def ylabel(self, text: str) -> None:
        if not text:
            return
        t = self.theme
        x = 14
        y = self.margin["top"] + self.plot_h / 2
        sz = 12 * self.font_scale
        self._parts.append(
            f'<text x="{x}" y="{y}" text-anchor="middle" '
            f'font-family="{t["font"]}" font-size="{sz:.1f}" fill="{t["muted"]}" '
            f'transform="rotate(-90 {x} {y})">{utils.escape_xml(text)}</text>'
        )

    def axes(
        self,
        x0: float,
        x1: float,
        y0: float,
        y1: float,
        grid: bool = True,
        xticks: list[float] | None = None,
        yticks: list[float] | None = None,
        xlabels: list[str] | None = None,
        categorical_x: bool = False,
        rotate_x: bool | float = False,
        log_x: bool = False,
        log_y: bool = False,
        datetime_x: bool = False,
        categorical_center: bool = True,
        xaxis_at: float | None = None,
        yaxis_at: float | None = None,
    ) -> None:
        self.x0 = x0
        self.x1 = x1
        self.y0 = y0
        self.y1 = y1
        self._logx = bool(log_x)
        self._logy = bool(log_y)
        t = self.theme
        if log_x:
            xt = xticks if xticks is not None else utils.log_ticks(x0, x1)
        else:
            xt = xticks if xticks is not None else utils.nice_ticks(x0, x1)
        if log_y:
            yt = yticks if yticks is not None else utils.log_ticks(y0, y1)
        else:
            yt = yticks if yticks is not None else utils.nice_ticks(y0, y1)

        # keep ticks inside domain (with tiny epsilon)
        def _in_y(v: float) -> bool:
            return y0 - 1e-12 <= v <= y1 + 1e-12

        def _in_x(v: float) -> bool:
            return x0 - 1e-12 <= v <= x1 + 1e-12

        # explicit tick lists (possibly empty) are honored exactly
        if yticks is not None:
            yt = [v for v in yt if _in_y(v)]
        else:
            yt = [v for v in yt if _in_y(v)] or [y0, y1]
        if not categorical_x:
            if xticks is not None:
                xt = [v for v in xt if _in_x(v)]
            else:
                xt = [v for v in xt if _in_x(v)] or [x0, x1]

        if grid:
            for y in yt:
                sy = self._sy(y, y0, y1)
                self._parts.append(
                    f'<line x1="{self.margin["left"]}" y1="{sy:.2f}" '
                    f'x2="{self.margin["left"] + self.plot_w}" y2="{sy:.2f}" '
                    f'stroke="{t["grid"]}" stroke-width="1" stroke-dasharray="2,4" stroke-opacity="0.5"/>'
                )
            if not categorical_x:
                for x in xt:
                    sx = self._sx(x, x0, x1)
                    self._parts.append(
                        f'<line x1="{sx:.2f}" y1="{self.margin["top"]}" '
                        f'x2="{sx:.2f}" y2="{self.margin["top"] + self.plot_h}" '
                        f'stroke="{t["grid"]}" stroke-width="1" stroke-dasharray="2,4" stroke-opacity="0.5"/>'
                    )

        bottom = self.margin["top"] + self.plot_h
        left = self.margin["left"]
        # axis lines normally hug the plot edges; bar charts may anchor them
        # at the zero line instead so the bars visually connect to the axes
        if xaxis_at is not None and y0 <= xaxis_at <= y1:
            xaxis_y = self._sy(xaxis_at, y0, y1)
        else:
            xaxis_y = bottom
        if yaxis_at is not None and x0 <= yaxis_at <= x1:
            yaxis_x = self._sx(yaxis_at, x0, x1)
        else:
            yaxis_x = left
        self._parts.append(
            f'<line x1="{left}" y1="{xaxis_y:.2f}" x2="{left + self.plot_w}" y2="{xaxis_y:.2f}" '
            f'stroke="{t["axis"]}" stroke-width="1.5"/>'
        )
        self._parts.append(
            f'<line x1="{yaxis_x:.2f}" y1="{self.margin["top"]}" x2="{yaxis_x:.2f}" y2="{bottom}" '
            f'stroke="{t["axis"]}" stroke-width="1.5"/>'
        )

        # Detect if x-axis is datetime-based (explicit flag or heuristic)
        is_datetime_x = bool(datetime_x) or (
            x0 > 1e8 and x1 > 1e8 and (x1 - x0) < 1e11
        )  # sensible range for Unix timestamps

        for y in yt:
            sy = self._sy(y, y0, y1)
            self._parts.append(
                f'<line x1="{left - 4}" y1="{sy:.2f}" x2="{left}" y2="{sy:.2f}" '
                f'stroke="{t["axis"]}" stroke-width="1"/>'
            )
            self._parts.append(
                f'<text x="{left - 8}" y="{sy + 4:.2f}" text-anchor="end" '
                f'font-family="{t["font"]}" font-size="11" fill="{t["muted"]}">'
                f"{utils.escape_xml(utils.format_number(y))}</text>"
            )

        # x tick label rotation: explicit angle wins, else auto rules
        if rotate_x not in (None, False):
            do_rotate = True
            angle = 35.0 if rotate_x is True else float(rotate_x)
        else:
            do_rotate = False
            angle = 35.0

        if categorical_x and xlabels is not None:
            n = len(xlabels)
            # auto-rotate if many / long labels
            max_len = max((len(str(l)) for l in xlabels), default=0)
            do_rotate = do_rotate or n > 8 or max_len > 10
            for i, lab in enumerate(xlabels):
                # bars/boxes are drawn at band centers; line/scatter points
                # sit on the band boundaries → ticks must match
                pos = i + 0.5 if categorical_center else i
                sx = self._sx(pos, 0, n) if n else left
                self._parts.append(
                    f'<line x1="{sx:.2f}" y1="{bottom}" x2="{sx:.2f}" y2="{bottom + 4}" '
                    f'stroke="{t["axis"]}" stroke-width="1"/>'
                )
                shown = utils.truncate_label(lab, 16)
                if do_rotate:
                    self._parts.append(
                        f'<text x="{sx:.2f}" y="{bottom + 12}" text-anchor="end" '
                        f'font-family="{t["font"]}" font-size="10" fill="{t["muted"]}" '
                        f'transform="rotate(-{angle:.0f} {sx:.2f} {bottom + 12})">'
                        f"{utils.escape_xml(shown)}</text>"
                    )
                else:
                    self._parts.append(
                        f'<text x="{sx:.2f}" y="{bottom + 18}" text-anchor="middle" '
                        f'font-family="{t["font"]}" font-size="11" fill="{t["muted"]}">'
                        f"{utils.escape_xml(shown)}</text>"
                    )
        else:
            # For datetime or crowded labels, rotate automatically
            do_rotate = do_rotate or is_datetime_x or len(xt) > 6
            for x in xt:
                sx = self._sx(x, x0, x1)
                self._parts.append(
                    f'<line x1="{sx:.2f}" y1="{bottom}" x2="{sx:.2f}" y2="{bottom + 4}" '
                    f'stroke="{t["axis"]}" stroke-width="1"/>'
                )
                label_text = utils.format_datetime_tick(x, x1 - x0) if is_datetime_x else utils.format_number(x)
                if do_rotate:
                    self._parts.append(
                        f'<text x="{sx:.2f}" y="{bottom + 12}" text-anchor="end" '
                        f'font-family="{t["font"]}" font-size="10" fill="{t["muted"]}" '
                        f'transform="rotate(-{angle:.0f} {sx:.2f} {bottom + 12})">'
                        f"{utils.escape_xml(label_text)}</text>"
                    )
                else:
                    self._parts.append(
                        f'<text x="{sx:.2f}" y="{bottom + 18}" text-anchor="middle" '
                        f'font-family="{t["font"]}" font-size="11" fill="{t["muted"]}">'
                        f"{utils.escape_xml(label_text)}</text>"
                    )

    def legend(self, items: list[tuple[str, str]], kind: str = "line",
               pos: str = "top-right") -> None:
        if not items:
            return
        t = self.theme
        max_len = max(len(lab) for lab, _ in items)
        box_w = min(240, (28 + max_len * 7.2) * self.font_scale)
        box_h = (8 + len(items) * 18) * self.font_scale
        if pos in ("top-left", "tl"):
            bx = self.margin["left"] + 8
            by = self.margin["top"] + 8
        elif pos in ("bottom-left", "bl"):
            bx = self.margin["left"] + 8
            by = self.margin["top"] + self.plot_h - box_h - 8
        elif pos in ("bottom-right", "br"):
            bx = self.margin["left"] + self.plot_w - box_w - 8
            by = self.margin["top"] + self.plot_h - box_h - 8
        else:
            bx = self.margin["left"] + self.plot_w - box_w - 8
            by = self.margin["top"] + 8
        self._parts.append(
            f'<rect x="{bx}" y="{by}" width="{box_w}" height="{box_h}" '
            f'rx="4" fill="{t["bg"]}" fill-opacity="0.92" '
            f'stroke="{t["grid"]}" stroke-width="1"/>'
        )
        for i, (lab, color) in enumerate(items):
            iy = by + (14 + i * 18) * self.font_scale
            if kind == "line":
                self._parts.append(
                    f'<line x1="{bx + 8 * self.font_scale}" y1="{iy}" x2="{bx + 24 * self.font_scale}" y2="{iy}" '
                    f'stroke="{color}" stroke-width="{2.5 * self.font_scale:.1f}" stroke-linecap="round"/>'
                )
                self._parts.append(
                    f'<circle cx="{bx + 16 * self.font_scale}" cy="{iy}" r="{3 * self.font_scale:.1f}" fill="{color}"/>'
                )
            elif kind == "bar":
                self._parts.append(
                    f'<rect x="{bx + 8 * self.font_scale}" y="{iy - 5 * self.font_scale}" width="{16 * self.font_scale:.1f}" height="{10 * self.font_scale:.1f}" '
                    f'rx="2" fill="{color}"/>'
                )
            else:
                self._parts.append(
                    f'<circle cx="{bx + 16 * self.font_scale}" cy="{iy}" r="{4 * self.font_scale:.1f}" fill="{color}"/>'
                )
            self._parts.append(
                f'<text x="{bx + 30 * self.font_scale}" y="{iy + 4 * self.font_scale}" font-family="{t["font"]}" '
                f'font-size="{11 * self.font_scale:.1f}" fill="{t["fg"]}">{utils.escape_xml(lab)}</text>'
            )

    # --- series -----------------------------------------------------------

    def _valid_pts(
        self,
        xs: Sequence[float],
        ys: Sequence[float],
        x0: float,
        x1: float,
        y0: float,
        y1: float,
    ) -> list[tuple[float, float]]:
        pts = []
        for x, y in zip(xs, ys):
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                continue
            if not math.isfinite(float(x)) or not math.isfinite(float(y)):
                continue
            pts.append((self._sx(float(x), x0, x1), self._sy(float(y), y0, y1)))
        return pts

    def line(
        self,
        xs: list[float],
        ys: list[float],
        x0: float,
        x1: float,
        y0: float,
        y1: float,
        color: str,
        width: float = 2.5,
        markers: bool = True,
        dashed: bool = False,
        step: bool = False,
    ) -> None:
        # Streaming renderer: points are scaled and formatted one at a time
        # and each completed segment is flushed straight into the SVG part
        # list.  No parallel scaled-tuple lists (segs / all_pts) are kept,
        # so transient memory stays proportional to the emitted SVG rather
        # than several hundred bytes per point.  (Also avoids the previous
        # O(n^2) string concatenation in step mode.)
        dash = ' stroke-dasharray="6,4"' if dashed else ""
        limit = 80  # markers are only drawn for series up to this many points
        marker_pts: list[tuple[float, float]] | None = [] if markers else None
        seg: list[str] = []   # formatted "x,y" coords of the current segment
        px = py = 0.0         # previous (scaled) point of the current segment

        def flush() -> None:
            if not seg:
                return
            if len(seg) == 1:
                self._parts.append(
                    f'<circle cx="{px:.2f}" cy="{py:.2f}" r="4" fill="{color}" '
                    f'clip-path="url(#{self._clip_id})"/>'
                )
            else:
                self._parts.append(
                    f'<path d="M {" L ".join(seg)}" fill="none" stroke="{color}" '
                    f'stroke-width="{width}" '
                    f'stroke-linecap="round" stroke-linejoin="round"{dash} '
                    f'clip-path="url(#{self._clip_id})"/>'
                )
            seg.clear()

        # fast linear mapping (covers the common non-log case); falls back to
        # the general _sx/_sy for log axes or degenerate ranges
        linear = (
            not self._logx
            and not self._logy
            and x1 != x0
            and y1 != y0
            and math.isfinite(x0)
            and math.isfinite(x1)
            and math.isfinite(y0)
            and math.isfinite(y1)
        )
        if linear:
            left = self.margin["left"]
            xsc = self.plot_w / (x1 - x0)
            ysc = -self.plot_h / (y1 - y0)
            yconst = self.margin["top"] + self.plot_h
        append = seg.append
        isfinite = math.isfinite

        for x, y in zip(xs, ys):
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                flush()
                continue
            fx = float(x)
            fy = float(y)
            if not isfinite(fx) or not isfinite(fy):
                flush()
                continue
            if linear:
                cx = left + (fx - x0) * xsc
                cy = yconst + (fy - y0) * ysc
            else:
                cx = self._sx(fx, x0, x1)
                cy = self._sy(fy, y0, y1)
            if step and seg:
                # post-step: hold y until the next x, then jump vertically
                append(f"{cx:.2f},{py:.2f}")
            append(f"{cx:.2f},{cy:.2f}")
            px, py = cx, cy
            if marker_pts is not None:
                if len(marker_pts) < limit:
                    marker_pts.append((cx, cy))
                else:
                    marker_pts = None  # too many points — markers are off
        flush()

        if marker_pts:
            for mx, my in marker_pts:
                self._parts.append(
                    f'<circle cx="{mx:.2f}" cy="{my:.2f}" r="3.5" fill="{color}" '
                    f'stroke="{self.theme["bg"]}" stroke-width="1.5" '
                    f'clip-path="url(#{self._clip_id})"/>'
                )

    def area(
        self,
        xs: list[float],
        ys: list[float],
        x0: float,
        x1: float,
        y0: float,
        y1: float,
        color: str,
        opacity: float = 0.25,
    ) -> None:
        # build per-gap segments (NaN breaks), then fill each polygon separately
        segs: list[list[tuple[float, float]]] = [[]]
        for x, y in zip(xs, ys):
            if (
                not isinstance(x, (int, float))
                or not isinstance(y, (int, float))
                or not math.isfinite(float(x))
                or not math.isfinite(float(y))
            ):
                if segs[-1]:
                    segs.append([])
                continue
            segs[-1].append((self._sx(float(x), x0, x1), self._sy(float(y), y0, y1)))
        baseline_y = 0.0 if y0 <= 0 <= y1 else y0
        baseline = self._sy(baseline_y, y0, y1)
        drew = False
        for pts in segs:
            if len(pts) < 2:
                continue
            d = "M " + " L ".join(f"{px:.2f},{py:.2f}" for px, py in pts)
            d += f" L {pts[-1][0]:.2f},{baseline:.2f} L {pts[0][0]:.2f},{baseline:.2f} Z"
            self._parts.append(
                f'<path d="{d}" fill="{color}" fill-opacity="{opacity}" '
                f'stroke="none" clip-path="url(#{self._clip_id})"/>'
            )
            drew = True
        if drew:
            self.line(xs, ys, x0, x1, y0, y1, color, width=2, markers=False)

    def scatter(
        self,
        xs: list[float],
        ys: list[float],
        x0: float,
        x1: float,
        y0: float,
        y1: float,
        color: str,
        size: float = 5,
        alpha: float = 0.85,
    ) -> None:
        size = max(0.5, float(size))
        alpha = min(1.0, max(0.0, float(alpha)))
        # fast linear mapping (falls back to _sx/_sy for log/degenerate ranges)
        linear = (
            not self._logx
            and not self._logy
            and x1 != x0
            and y1 != y0
            and math.isfinite(x0)
            and math.isfinite(x1)
            and math.isfinite(y0)
            and math.isfinite(y1)
        )
        if linear:
            left = self.margin["left"]
            xsc = self.plot_w / (x1 - x0)
            ysc = -self.plot_h / (y1 - y0)
            yconst = self.margin["top"] + self.plot_h
        isfinite = math.isfinite
        append = self._parts.append
        for x, y in zip(xs, ys):
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                continue
            fx = float(x)
            fy = float(y)
            if not isfinite(fx) or not isfinite(fy):
                continue
            if linear:
                sx = left + (fx - x0) * xsc
                sy = yconst + (fy - y0) * ysc
            else:
                sx = self._sx(fx, x0, x1)
                sy = self._sy(fy, y0, y1)
            append(
                f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="{size}" fill="{color}" '
                f'fill-opacity="{alpha}" clip-path="url(#{self._clip_id})"/>'
            )

    def bars_v(
        self,
        n: int,
        values: list[float],
        y0: float,
        y1: float,
        colors: list[str],
        gap: float = 0.28,
        group: int = 0,
        n_groups: int = 1,
        show_values: bool = False,
        value_fmt: str | None = None,
    ) -> None:
        if n <= 0:
            return
        band = self.plot_w / n
        gap = min(0.8, max(0.0, gap))
        if n_groups > 1:
            inner = band * (1 - gap)
            bar_w = max(1.0, inner / n_groups)
            offset = group * bar_w
            left_pad = band * gap / 2
        else:
            bar_w = max(1.0, band * (1 - gap))
            offset = 0
            left_pad = band * gap / 2

        t = self.theme
        for i, val in enumerate(values):
            if i >= n:
                break
            if not isinstance(val, (int, float)) or not math.isfinite(float(val)):
                continue
            val = float(val)
            color = colors[i % len(colors)] if n_groups == 1 else colors[group % len(colors)]
            x = self.margin["left"] + i * band + left_pad + offset
            y_top = self._sy(val, y0, y1)
            base_val = 0.0 if y0 <= 0 <= y1 else y0
            y_base = self._sy(base_val, y0, y1)
            top = min(y_top, y_base)
            h = max(abs(y_base - y_top), 0.5)
            self._parts.append(
                f'<rect x="{x:.2f}" y="{top:.2f}" width="{bar_w:.2f}" height="{h:.2f}" '
                f'rx="3" fill="{color}" clip-path="url(#{self._clip_id})"/>'
            )
            if show_values and bar_w >= 14:
                ty = top - 4 if val >= base_val else top + h + 12
                lab = value_fmt.format(val) if value_fmt else utils.format_number(val)
                self._parts.append(
                    f'<text x="{x + bar_w/2:.2f}" y="{ty:.2f}" text-anchor="middle" '
                    f'font-family="{t["font"]}" font-size="10" fill="{t["muted"]}">'
                    f"{utils.escape_xml(lab)}</text>"
                )

    def bars_h(
        self,
        n: int,
        values: list[float],
        x0: float,
        x1: float,
        colors: list[str],
        categories: list[str],
        gap: float = 0.28,
        show_values: bool = False,
        value_fmt: str | None = None,
    ) -> None:
        """Horizontal bars; value mapped on x-axis, categories on y."""
        if n <= 0:
            return
        band = self.plot_h / n
        bar_h = max(1.0, band * (1 - gap))
        t = self.theme
        for i, val in enumerate(values):
            if i >= n:
                break
            if not isinstance(val, (int, float)) or not math.isfinite(float(val)):
                continue
            val = float(val)
            color = colors[i % len(colors)]
            y = self.margin["top"] + i * band + band * gap / 2
            base_val = 0.0 if x0 <= 0 <= x1 else x0
            x_base = self._sx(base_val, x0, x1)
            x_end = self._sx(val, x0, x1)
            left = min(x_base, x_end)
            w = max(abs(x_end - x_base), 0.5)
            self._parts.append(
                f'<rect x="{left:.2f}" y="{y:.2f}" width="{w:.2f}" height="{bar_h:.2f}" '
                f'rx="3" fill="{color}" clip-path="url(#{self._clip_id})"/>'
            )
            # category label on left
            lab = utils.truncate_label(categories[i] if i < len(categories) else str(i), 14)
            cy = y + bar_h / 2 + 4
            self._parts.append(
                f'<text x="{self.margin["left"] - 8}" y="{cy:.2f}" text-anchor="end" '
                f'font-family="{t["font"]}" font-size="11" fill="{t["muted"]}">'
                f"{utils.escape_xml(lab)}</text>"
            )
            # value label at the bar end
            if show_values and bar_h >= 12:
                vlab = value_fmt.format(val) if value_fmt else utils.format_number(val)
                anchor = "start" if val >= base_val else "end"
                vx = x_end + 4 if val >= base_val else x_end - 4
                self._parts.append(
                    f'<text x="{vx:.2f}" y="{cy:.2f}" text-anchor="{anchor}" '
                    f'font-family="{t["font"]}" font-size="10" fill="{t["muted"]}">'
                    f"{utils.escape_xml(vlab)}</text>"
                )

    def pie(
        self,
        values: list[float],
        labels: list[str],
        colors: list[str],
        donut: bool = False,
    ) -> None:
        clean: list[tuple[int, float]] = []
        for i, v in enumerate(values):
            if isinstance(v, (int, float)) and math.isfinite(float(v)) and float(v) > 0:
                clean.append((i, float(v)))
        total = sum(v for _, v in clean)
        if total <= 0:
            self.empty_message("No positive values")
            return

        t = self.theme
        cx = self.width / 2
        cy = self.margin["top"] + self.plot_h / 2
        r = min(self.plot_w, self.plot_h) * 0.36
        inner = r * 0.55 if donut else 0.0

        # leave room for labels: shrink if many slices
        if len(clean) > 6:
            r *= 0.92

        angle = -math.pi / 2
        for i, val in clean:
            sweep = 2 * math.pi * (val / total)
            # full circle special-case (SVG arc can't draw 360° as one arc)
            if sweep >= 2 * math.pi - 1e-9:
                self._parts.append(
                    f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{colors[i % len(colors)]}"/>'
                )
                if donut and inner > 0:
                    self._parts.append(
                        f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{inner:.2f}" fill="{t["bg"]}"/>'
                    )
                lab = labels[i] if i < len(labels) else f"#{i+1}"
                self._parts.append(
                    f'<text x="{cx:.2f}" y="{cy - r - 10:.2f}" text-anchor="middle" '
                    f'font-family="{t["font"]}" font-size="11" fill="{t["fg"]}">'
                    f"{utils.escape_xml(lab)} (100%)</text>"
                )
                return

            a0, a1 = angle, angle + sweep
            color = colors[i % len(colors)]
            large = 1 if sweep > math.pi else 0
            x0p = cx + r * math.cos(a0)
            y0p = cy + r * math.sin(a0)
            x1p = cx + r * math.cos(a1)
            y1p = cy + r * math.sin(a1)

            if donut and inner > 0:
                ix0 = cx + inner * math.cos(a0)
                iy0 = cy + inner * math.sin(a0)
                ix1 = cx + inner * math.cos(a1)
                iy1 = cy + inner * math.sin(a1)
                d = (
                    f"M {x0p:.2f},{y0p:.2f} "
                    f"A {r:.2f},{r:.2f} 0 {large} 1 {x1p:.2f},{y1p:.2f} "
                    f"L {ix1:.2f},{iy1:.2f} "
                    f"A {inner:.2f},{inner:.2f} 0 {large} 0 {ix0:.2f},{iy0:.2f} Z"
                )
            else:
                d = (
                    f"M {cx:.2f},{cy:.2f} L {x0p:.2f},{y0p:.2f} "
                    f"A {r:.2f},{r:.2f} 0 {large} 1 {x1p:.2f},{y1p:.2f} Z"
                )
            self._parts.append(
                f'<path d="{d}" fill="{color}" stroke="{t["bg"]}" stroke-width="2"/>'
            )

            mid = a0 + sweep / 2
            # only label slices that are large enough
            pct = val / total * 100
            if pct >= 3 or len(clean) <= 6:
                lr = r * 1.2
                lx = cx + lr * math.cos(mid)
                ly = cy + lr * math.sin(mid)
                anchor = "start" if math.cos(mid) >= 0 else "end"
                lab = labels[i] if i < len(labels) else f"#{i+1}"
                self._parts.append(
                    f'<text x="{lx:.2f}" y="{ly:.2f}" text-anchor="{anchor}" '
                    f'font-family="{t["font"]}" font-size="11" fill="{t["fg"]}">'
                    f"{utils.escape_xml(str(lab))} ({pct:.0f}%)</text>"
                )
            angle = a1


    def subtitle(self, text: str) -> None:
        if not text:
            return
        t = self.theme
        sz = 12 * self.font_scale
        self._parts.append(
            f'<text x="{self.width / 2}" y="44" text-anchor="middle" '
            f'font-family="{t["font"]}" font-size="{sz:.1f}" '
            f'fill="{t["muted"]}">{utils.escape_xml(text)}</text>'
        )

    def footnote(self, text: str) -> None:
        if not text:
            return
        t = self.theme
        sz = 10 * self.font_scale
        self._parts.append(
            f'<text x="{self.margin["left"]}" y="{self.height - 6}" text-anchor="start" '
            f'font-family="{t["font"]}" font-size="{sz:.1f}" '
            f'fill="{t["muted"]}">{utils.escape_xml(text)}</text>'
        )

    def hline(self, y: float, y0: float, y1: float, color: str,
              dashed: bool = True, width: float = 1.5) -> None:
        sy = self._sy(y, y0, y1)
        dash = ' stroke-dasharray="5,4"' if dashed else ""
        self._parts.append(
            f'<line x1="{self.margin["left"]}" y1="{sy:.2f}" '
            f'x2="{self.margin["left"] + self.plot_w}" y2="{sy:.2f}" '
            f'stroke="{color}" stroke-width="{width}"{dash} '
            f'clip-path="url(#{self._clip_id})"/>'
        )

    def vline(self, x: float, x0: float, x1: float, color: str,
              dashed: bool = True, width: float = 1.5) -> None:
        sx = self._sx(x, x0, x1)
        dash = ' stroke-dasharray="5,4"' if dashed else ""
        self._parts.append(
            f'<line x1="{sx:.2f}" y1="{self.margin["top"]}" '
            f'x2="{sx:.2f}" y2="{self.margin["top"] + self.plot_h}" '
            f'stroke="{color}" stroke-width="{width}"{dash} '
            f'clip-path="url(#{self._clip_id})"/>'
        )

    def annotate(self, x: float, y: float, x0: float, x1: float, y0: float, y1: float,
                 text: str, color: str | None = None, anchor: str = "start",
                 size: float = 11) -> None:
        t = self.theme
        sx, sy = self._sx(x, x0, x1), self._sy(y, y0, y1)
        col = color or t["fg"]
        sz = float(size) * self.font_scale
        a = anchor if anchor in ("start", "middle", "end") else "start"
        # offset the label away from the point depending on its anchor
        dx = {"start": 7, "middle": 0, "end": -7}[a]
        self._parts.append(
            f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="3" fill="{col}" '
            f'clip-path="url(#{self._clip_id})"/>'
        )
        self._parts.append(
            f'<text x="{sx + dx:.2f}" y="{sy - 6:.2f}" text-anchor="{a}" '
            f'font-family="{t["font"]}" font-size="{sz:.1f}" fill="{col}" '
            f'clip-path="url(#{self._clip_id})">{utils.escape_xml(text)}</text>'
        )

    def boxplot(
        self,
        stats: list[dict],
        v0: float,
        v1: float,
        colors: list[str],
        labels: list[str] | None = None,
        horizontal: bool = False,
        width: float = 1.5,
    ) -> None:
        """Draw Tukey boxplots. stats: list of box_stats() dicts."""
        n = len(stats)
        if n == 0:
            return
        t = self.theme
        if horizontal:
            band = self.plot_h / n
            for i, b in enumerate(stats):
                color = colors[i % len(colors)]
                cy = self.margin["top"] + (i + 0.5) * band
                h = max(4.0, band * 0.5)
                q1x, q3x = self._sx(b["q1"], v0, v1), self._sx(b["q3"], v0, v1)
                mx = self._sx(b["med"], v0, v1)
                lox, hix = self._sx(b["lo"], v0, v1), self._sx(b["hi"], v0, v1)
                cstr, a = svg_color_alpha(color, 0.35)
                x = min(q1x, q3x)
                w = abs(q3x - q1x)
                self._parts.append(
                    f'<rect x="{x:.2f}" y="{cy - h / 2:.2f}" width="{w:.2f}" height="{h:.2f}" '
                    f'rx="2" fill="{cstr}" fill-opacity="{a:.3f}" stroke="{color}" stroke-width="{width}" '
                    f'clip-path="url(#{self._clip_id})"/>'
                )
                self._parts.append(
                    f'<line x1="{lox:.2f}" y1="{cy:.2f}" x2="{q1x:.2f}" y2="{cy:.2f}" '
                    f'stroke="{color}" stroke-width="{width}" clip-path="url(#{self._clip_id})"/>'
                )
                self._parts.append(
                    f'<line x1="{q3x:.2f}" y1="{cy:.2f}" x2="{hix:.2f}" y2="{cy:.2f}" '
                    f'stroke="{color}" stroke-width="{width}" clip-path="url(#{self._clip_id})"/>'
                )
                self._parts.append(
                    f'<line x1="{lox:.2f}" y1="{cy - h / 2:.2f}" x2="{lox:.2f}" y2="{cy + h / 2:.2f}" '
                    f'stroke="{color}" stroke-width="{width}" clip-path="url(#{self._clip_id})"/>'
                )
                self._parts.append(
                    f'<line x1="{hix:.2f}" y1="{cy - h / 2:.2f}" x2="{hix:.2f}" y2="{cy + h / 2:.2f}" '
                    f'stroke="{color}" stroke-width="{width}" clip-path="url(#{self._clip_id})"/>'
                )
                self._parts.append(
                    f'<line x1="{mx:.2f}" y1="{cy - h / 2:.2f}" x2="{mx:.2f}" y2="{cy + h / 2:.2f}" '
                    f'stroke="{t["fg"]}" stroke-width="{width + 0.5}" clip-path="url(#{self._clip_id})"/>'
                )
                for out in b.get("outliers") or []:
                    ox = self._sx(out, v0, v1)
                    self._parts.append(
                        f'<circle cx="{ox:.2f}" cy="{cy:.2f}" r="3" fill="none" '
                        f'stroke="{color}" stroke-width="{width}" clip-path="url(#{self._clip_id})"/>'
                    )
                if labels:
                    lab = utils.truncate_label(labels[i] if i < len(labels) else str(i + 1), 14)
                    self._parts.append(
                        f'<text x="{self.margin["left"] - 8}" y="{cy + 4:.2f}" text-anchor="end" '
                        f'font-family="{t["font"]}" font-size="11" fill="{t["muted"]}">'
                        f"{utils.escape_xml(lab)}</text>"
                    )
        else:
            band = self.plot_w / n
            for i, b in enumerate(stats):
                color = colors[i % len(colors)]
                cx = self.margin["left"] + (i + 0.5) * band
                w = max(4.0, band * 0.5)
                q1y, q3y = self._sy(b["q1"], v0, v1), self._sy(b["q3"], v0, v1)
                my = self._sy(b["med"], v0, v1)
                loy, hiy = self._sy(b["lo"], v0, v1), self._sy(b["hi"], v0, v1)
                cstr, a = svg_color_alpha(color, 0.35)
                y = min(q1y, q3y)
                h = abs(q3y - q1y)
                self._parts.append(
                    f'<rect x="{cx - w / 2:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
                    f'rx="2" fill="{cstr}" fill-opacity="{a:.3f}" stroke="{color}" stroke-width="{width}" '
                    f'clip-path="url(#{self._clip_id})"/>'
                )
                self._parts.append(
                    f'<line x1="{cx:.2f}" y1="{loy:.2f}" x2="{cx:.2f}" y2="{q1y:.2f}" '
                    f'stroke="{color}" stroke-width="{width}" clip-path="url(#{self._clip_id})"/>'
                )
                self._parts.append(
                    f'<line x1="{cx:.2f}" y1="{q3y:.2f}" x2="{cx:.2f}" y2="{hiy:.2f}" '
                    f'stroke="{color}" stroke-width="{width}" clip-path="url(#{self._clip_id})"/>'
                )
                self._parts.append(
                    f'<line x1="{cx - w / 2:.2f}" y1="{loy:.2f}" x2="{cx + w / 2:.2f}" y2="{loy:.2f}" '
                    f'stroke="{color}" stroke-width="{width}" clip-path="url(#{self._clip_id})"/>'
                )
                self._parts.append(
                    f'<line x1="{cx - w / 2:.2f}" y1="{hiy:.2f}" x2="{cx + w / 2:.2f}" y2="{hiy:.2f}" '
                    f'stroke="{color}" stroke-width="{width}" clip-path="url(#{self._clip_id})"/>'
                )
                self._parts.append(
                    f'<line x1="{cx - w / 2:.2f}" y1="{my:.2f}" x2="{cx + w / 2:.2f}" y2="{my:.2f}" '
                    f'stroke="{t["fg"]}" stroke-width="{width + 0.5}" clip-path="url(#{self._clip_id})"/>'
                )
                for out in b.get("outliers") or []:
                    oy = self._sy(out, v0, v1)
                    self._parts.append(
                        f'<circle cx="{cx:.2f}" cy="{oy:.2f}" r="3" fill="none" '
                        f'stroke="{color}" stroke-width="{width}" clip-path="url(#{self._clip_id})"/>'
                    )

    def heatmap(
        self,
        matrix: list[list[float | None]],
        colors: list[list[str]],
        nan_color: str,
        show_values: bool = True,
        value_fmt: str | None = None,
    ) -> None:
        """Draw a heatmap cell grid across the full plot area."""
        rows = len(matrix)
        if rows == 0:
            self.empty_message("No data")
            return
        cols = max(len(r) for r in matrix)
        if cols == 0:
            self.empty_message("No data")
            return
        cell_w = self.plot_w / cols
        cell_h = self.plot_h / rows
        t = self.theme
        left = self.margin["left"]
        top = self.margin["top"]
        for i, row in enumerate(matrix):
            for j, v in enumerate(row):
                color = colors[i][j] if v is not None else nan_color
                self._parts.append(
                    f'<rect x="{left + j * cell_w:.2f}" y="{top + i * cell_h:.2f}" '
                    f'width="{cell_w + 0.5:.2f}" height="{cell_h + 0.5:.2f}" fill="{color}"/>'
                )
                if show_values and v is not None and cell_w >= 34 and cell_h >= 16:
                    lab = value_fmt.format(v) if value_fmt else utils.format_number(v)
                    lum = 0.299 * int(color[1:3], 16) + 0.587 * int(color[3:5], 16) + 0.114 * int(color[5:7], 16)
                    text_col = "#0f172a" if lum > 150 else "#f8fafc"
                    self._parts.append(
                        f'<text x="{left + (j + 0.5) * cell_w:.2f}" y="{top + (i + 0.5) * cell_h + 4:.2f}" '
                        f'text-anchor="middle" font-family="{t["font"]}" font-size="10" fill="{text_col}">'
                        f"{utils.escape_xml(lab)}</text>"
                    )

    def heat_colorbar(self, c0: str, c1: str, vmin: float, vmax: float) -> None:
        """Vertical colorbar legend at the right side of the plot area."""
        t = self.theme
        x = self.margin["left"] + self.plot_w + 12
        top = self.margin["top"]
        h = self.plot_h
        steps = 24
        for s in range(steps):
            col = utils.interp_color(c0, c1, s / max(steps - 1, 1))
            y = top + h * s / steps
            self._parts.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="14" height="{h / steps + 0.5:.2f}" fill="{col}"/>'
            )
        self._parts.append(
            f'<rect x="{x:.2f}" y="{top:.2f}" width="14" height="{h:.2f}" '
            f'fill="none" stroke="{t["grid"]}" stroke-width="1"/>'
        )
        self._parts.append(
            f'<text x="{x + 7:.2f}" y="{top - 4:.2f}" text-anchor="middle" '
            f'font-family="{t["font"]}" font-size="9" fill="{t["muted"]}">'
            f"{utils.escape_xml(utils.format_number(vmax))}</text>"
        )
        self._parts.append(
            f'<text x="{x + 7:.2f}" y="{top + h + 12:.2f}" text-anchor="middle" '
            f'font-family="{t["font"]}" font-size="9" fill="{t["muted"]}">'
            f"{utils.escape_xml(utils.format_number(vmin))}</text>"
        )

    def bars_stacked(
        self,
        n: int,
        series_values: list[list[float]],
        y0: float,
        y1: float,
        colors: list[str],
        gap: float = 0.28,
    ) -> None:
        if n <= 0 or not series_values:
            return
        band = self.plot_w / n
        bar_w = max(1.0, band * (1 - gap))
        left_pad = band * gap / 2
        for i in range(n):
            pos_base = 0.0
            neg_base = 0.0
            for si, vals in enumerate(series_values):
                if i >= len(vals):
                    continue
                val = vals[i]
                if not isinstance(val, (int, float)):
                    continue
                val = float(val)
                if not math.isfinite(val) or val == 0:
                    continue
                color = colors[si % len(colors)]
                x = self.margin["left"] + i * band + left_pad
                start = pos_base if val > 0 else neg_base
                end = start + val
                y_top = self._sy(end, y0, y1)
                y_bot = self._sy(start, y0, y1)
                top = min(y_top, y_bot)
                h = max(abs(y_bot - y_top), 0.5)
                self._parts.append(
                    f'<rect x="{x:.2f}" y="{top:.2f}" width="{bar_w:.2f}" height="{h:.2f}" '
                    f'rx="2" fill="{color}" clip-path="url(#{self._clip_id})"/>'
                )
                if val > 0:
                    pos_base = end
                else:
                    neg_base = end

    def to_pixels(self, x: float, y: float) -> tuple[float, float]:
        """Convert data coordinates to pixel/pixel-relative coordinates."""
        return self._sx(x, self.x0, self.x1), self._sy(y, self.y0, self.y1)

    def draw_line(self, x1: float, y1: float, x2: float, y2: float, color: str, width: float = 1.5, dashed: bool = False, raw_coords: bool = False, opacity: float = 1.0) -> None:
        """Draw a primitive line. By default uses data coordinates unless raw_coords=True."""
        px1, py1 = (x1, y1) if raw_coords else self.to_pixels(x1, y1)
        px2, py2 = (x2, y2) if raw_coords else self.to_pixels(x2, y2)
        if not raw_coords:
            clipped = utils.clip_line_to_rect(
                px1,
                py1,
                px2,
                py2,
                self.margin["left"],
                self.margin["top"],
                self.margin["left"] + self.plot_w,
                self.margin["top"] + self.plot_h,
            )
            if clipped is None:
                return
            px1, py1, px2, py2 = clipped
        dash = ' stroke-dasharray="5,4"' if dashed else ""
        clip_attr = '' if raw_coords else f' clip-path="url(#{self._clip_id})"'
        color_str, final_a = svg_color_alpha(color, opacity)
        self._parts.append(
            f'<line x1="{px1:.2f}" y1="{py1:.2f}" x2="{px2:.2f}" y2="{py2:.2f}" '
            f'stroke="{color_str}" stroke-opacity="{final_a:.3f}" stroke-width="{width:.2f}"{dash}{clip_attr}/>'
        )

    def draw_rect(self, x: float, y: float, w: float, h: float, color: str, fill: bool = True, stroke_color: str | None = None, stroke_width: float = 1.0, radius: float = 0.0, raw_coords: bool = False, opacity: float = 1.0) -> None:
        """Draw a primitive rectangle. Coordinates are in data coordinates unless raw_coords=True."""
        px, py = (x, y) if raw_coords else self.to_pixels(x, y)
        pw, ph = w, h
        if not raw_coords:
            # map width/height using scale
            px2, py2 = self.to_pixels(x + w, y + h)
            pw = abs(px2 - px)
            ph = abs(py2 - py)
            px = min(px, px2)
            py = min(py, py2)

        color_str, final_a = svg_color_alpha(color, opacity)
        f_attr = f'fill="{color_str}" fill-opacity="{final_a:.3f}"' if fill else 'fill="none"'
        if stroke_color:
            sc_str, sc_final_a = svg_color_alpha(stroke_color, opacity)
            s_attr = f' stroke="{sc_str}" stroke-opacity="{sc_final_a:.3f}" stroke-width="{stroke_width:.2f}"'
        else:
            s_attr = ' stroke="none"'
        r_attr = f' rx="{radius:.2f}"' if radius > 0 else ""
        clip_attr = '' if raw_coords else f' clip-path="url(#{self._clip_id})"'
        self._parts.append(
            f'<rect x="{px:.2f}" y="{py:.2f}" width="{pw:.2f}" height="{ph:.2f}"'
            f'{r_attr} {f_attr}{s_attr}{clip_attr}/>'
        )

    def draw_circle(self, cx: float, cy: float, r: float, color: str, fill: bool = True, stroke_color: str | None = None, stroke_width: float = 1.0, raw_coords: bool = False, opacity: float = 1.0) -> None:
        """Draw a primitive circle. Center is in data coordinates unless raw_coords=True."""
        pcx, pcy = (cx, cy) if raw_coords else self.to_pixels(cx, cy)
        color_str, final_a = svg_color_alpha(color, opacity)
        f_attr = f'fill="{color_str}" fill-opacity="{final_a:.3f}"' if fill else 'fill="none"'
        if stroke_color:
            sc_str, sc_final_a = svg_color_alpha(stroke_color, opacity)
            s_attr = f' stroke="{sc_str}" stroke-opacity="{sc_final_a:.3f}" stroke-width="{stroke_width:.2f}"'
        else:
            s_attr = ' stroke="none"'
        clip_attr = '' if raw_coords else f' clip-path="url(#{self._clip_id})"'
        self._parts.append(
            f'<circle cx="{pcx:.2f}" cy="{pcy:.2f}" r="{r:.2f}" '
            f'{f_attr}{s_attr}{clip_attr}/>'
        )

    def draw_text(self, x: float, y: float, text: str, color: str, size: float = 11, align: str = "start", raw_coords: bool = False, opacity: float = 1.0) -> None:
        """Draw primitive text at the given coordinate."""
        px, py = (x, y) if raw_coords else self.to_pixels(x, y)
        t = self.theme
        anchor = "start" if align in ("start", "left") else ("end" if align in ("end", "right") else "middle")
        color_str, final_a = svg_color_alpha(color, opacity)

        # scale size with font_scale
        scale_fac = getattr(self, "font_scale", 1.0)
        final_size = size * scale_fac

        clip_attr = '' if raw_coords else f' clip-path="url(#{self._clip_id})"'
        self._parts.append(
            f'<text x="{px:.2f}" y="{py:.2f}" text-anchor="{anchor}" '
            f'font-family="{t["font"]}" font-size="{final_size:.1f}" fill="{color_str}" fill-opacity="{final_a:.3f}"'
            f'{clip_attr}>{utils.escape_xml(text)}</text>'
        )

    def draw_polygon(self, pts: Sequence[tuple[float, float]], color: str, fill: bool = True, stroke_color: str | None = None, stroke_width: float = 1.0, raw_coords: bool = False, opacity: float = 1.0) -> None:
        """Draw primitive polygon. Points are a sequence of (x, y) in data coordinates unless raw_coords=True."""
        mapped_pts = []
        for x, y in pts:
            px, py = (x, y) if raw_coords else self.to_pixels(x, y)
            mapped_pts.append(f"{px:.2f},{py:.2f}")
        pts_str = " ".join(mapped_pts)
        color_str, final_a = svg_color_alpha(color, opacity)
        f_attr = f'fill="{color_str}" fill-opacity="{final_a:.3f}"' if fill else 'fill="none"'
        if stroke_color:
            sc_str, sc_final_a = svg_color_alpha(stroke_color, opacity)
            s_attr = f' stroke="{sc_str}" stroke-opacity="{sc_final_a:.3f}" stroke-width="{stroke_width:.2f}"'
        else:
            s_attr = ' stroke="none"'
        clip_attr = '' if raw_coords else f' clip-path="url(#{self._clip_id})"'
        self._parts.append(
            f'<polygon points="{pts_str}" {f_attr}{s_attr}{clip_attr}/>'
        )

    def hspan(self, ymin: float, ymax: float, y0: float, y1: float, color: str, alpha: float = 0.25) -> None:
        sy1 = self._sy(ymin, y0, y1)
        sy2 = self._sy(ymax, y0, y1)
        y = min(sy1, sy2)
        h = abs(sy1 - sy2)
        self.draw_rect(self.margin["left"], y, self.plot_w, h, color, fill=True, opacity=alpha, raw_coords=True)

    def vspan(self, xmin: float, xmax: float, x0: float, x1: float, color: str, alpha: float = 0.25) -> None:
        sx1 = self._sx(xmin, x0, x1)
        sx2 = self._sx(xmax, x0, x1)
        x = min(sx1, sx2)
        w = abs(sx1 - sx2)
        self.draw_rect(x, self.margin["top"], w, self.plot_h, color, fill=True, opacity=alpha, raw_coords=True)

    def finish(self) -> str:
        defs = f"<defs>{''.join(self._defs)}</defs>" if self._defs else ""
        body = "\n  ".join(self._parts)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}">\n'
            f"  {defs}\n"
            f"  {body}\n"
            f"</svg>\n"
        )
