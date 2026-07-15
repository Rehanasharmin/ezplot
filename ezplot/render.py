"""Pure-Python SVG renderer — fast, zero dependencies, multi-chart safe."""

from __future__ import annotations

import math
from typing import Sequence

from . import utils
from .style import get_theme


class SVGRenderer:
    """Draw chart series into an SVG string."""

    def __init__(
        self,
        width: int = 720,
        height: int = 420,
        theme: str | None = None,
        margin: dict | None = None,
    ):
        self.width = max(120, int(width))
        self.height = max(100, int(height))
        self.theme = get_theme(theme)
        self.margin = dict(margin or {"top": 48, "right": 28, "bottom": 56, "left": 64})
        self._parts: list[str] = []
        self._defs: list[str] = []
        self._clip_id = utils.unique_id("c")
        self._grad_i = 0

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
        if x1 == x0 or not math.isfinite(x0) or not math.isfinite(x1):
            return self.margin["left"] + self.plot_w / 2
        return self.margin["left"] + (x - x0) / (x1 - x0) * self.plot_w

    def _sy(self, y: float, y0: float, y1: float) -> float:
        if not math.isfinite(y):
            return self.margin["top"] + self.plot_h / 2
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
        self._parts.append(
            f'<text x="{self.width/2}" y="{self.height/2}" text-anchor="middle" '
            f'font-family="{t["font"]}" font-size="14" fill="{t["muted"]}">'
            f"{utils.escape_xml(msg)}</text>"
        )

    def title(self, text: str) -> None:
        if not text:
            return
        t = self.theme
        self._parts.append(
            f'<text x="{self.width / 2}" y="28" text-anchor="middle" '
            f'font-family="{t["font"]}" font-size="16" font-weight="600" '
            f'fill="{t["title"]}">{utils.escape_xml(text)}</text>'
        )

    def xlabel(self, text: str) -> None:
        if not text:
            return
        t = self.theme
        y = self.height - 12
        self._parts.append(
            f'<text x="{self.margin["left"] + self.plot_w / 2}" y="{y}" '
            f'text-anchor="middle" font-family="{t["font"]}" font-size="12" '
            f'fill="{t["muted"]}">{utils.escape_xml(text)}</text>'
        )

    def ylabel(self, text: str) -> None:
        if not text:
            return
        t = self.theme
        x = 14
        y = self.margin["top"] + self.plot_h / 2
        self._parts.append(
            f'<text x="{x}" y="{y}" text-anchor="middle" '
            f'font-family="{t["font"]}" font-size="12" fill="{t["muted"]}" '
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
        rotate_x: bool = False,
    ) -> None:
        t = self.theme
        xt = xticks if xticks is not None else utils.nice_ticks(x0, x1)
        yt = yticks if yticks is not None else utils.nice_ticks(y0, y1)

        # keep ticks inside domain (with tiny epsilon)
        def _in_y(v: float) -> bool:
            return y0 - 1e-12 <= v <= y1 + 1e-12

        def _in_x(v: float) -> bool:
            return x0 - 1e-12 <= v <= x1 + 1e-12

        yt = [v for v in yt if _in_y(v)] or [y0, y1]
        if not categorical_x:
            xt = [v for v in xt if _in_x(v)] or [x0, x1]

        if grid:
            for y in yt:
                sy = self._sy(y, y0, y1)
                self._parts.append(
                    f'<line x1="{self.margin["left"]}" y1="{sy:.2f}" '
                    f'x2="{self.margin["left"] + self.plot_w}" y2="{sy:.2f}" '
                    f'stroke="{t["grid"]}" stroke-width="1"/>'
                )
            if not categorical_x:
                for x in xt:
                    sx = self._sx(x, x0, x1)
                    self._parts.append(
                        f'<line x1="{sx:.2f}" y1="{self.margin["top"]}" '
                        f'x2="{sx:.2f}" y2="{self.margin["top"] + self.plot_h}" '
                        f'stroke="{t["grid"]}" stroke-width="1" stroke-dasharray="2,3"/>'
                    )

        bottom = self.margin["top"] + self.plot_h
        left = self.margin["left"]
        self._parts.append(
            f'<line x1="{left}" y1="{bottom}" x2="{left + self.plot_w}" y2="{bottom}" '
            f'stroke="{t["axis"]}" stroke-width="1.5"/>'
        )
        self._parts.append(
            f'<line x1="{left}" y1="{self.margin["top"]}" x2="{left}" y2="{bottom}" '
            f'stroke="{t["axis"]}" stroke-width="1.5"/>'
        )

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

        if categorical_x and xlabels is not None:
            n = len(xlabels)
            # auto-rotate if many / long labels
            max_len = max((len(str(l)) for l in xlabels), default=0)
            do_rotate = rotate_x or n > 8 or max_len > 10
            for i, lab in enumerate(xlabels):
                sx = self._sx(i + 0.5, 0, n) if n else left
                self._parts.append(
                    f'<line x1="{sx:.2f}" y1="{bottom}" x2="{sx:.2f}" y2="{bottom + 4}" '
                    f'stroke="{t["axis"]}" stroke-width="1"/>'
                )
                shown = utils.truncate_label(lab, 16)
                if do_rotate:
                    self._parts.append(
                        f'<text x="{sx:.2f}" y="{bottom + 12}" text-anchor="end" '
                        f'font-family="{t["font"]}" font-size="10" fill="{t["muted"]}" '
                        f'transform="rotate(-35 {sx:.2f} {bottom + 12})">'
                        f"{utils.escape_xml(shown)}</text>"
                    )
                else:
                    self._parts.append(
                        f'<text x="{sx:.2f}" y="{bottom + 18}" text-anchor="middle" '
                        f'font-family="{t["font"]}" font-size="11" fill="{t["muted"]}">'
                        f"{utils.escape_xml(shown)}</text>"
                    )
        else:
            for x in xt:
                sx = self._sx(x, x0, x1)
                self._parts.append(
                    f'<line x1="{sx:.2f}" y1="{bottom}" x2="{sx:.2f}" y2="{bottom + 4}" '
                    f'stroke="{t["axis"]}" stroke-width="1"/>'
                )
                self._parts.append(
                    f'<text x="{sx:.2f}" y="{bottom + 18}" text-anchor="middle" '
                    f'font-family="{t["font"]}" font-size="11" fill="{t["muted"]}">'
                    f"{utils.escape_xml(utils.format_number(x))}</text>"
                )

    def legend(self, items: list[tuple[str, str]], kind: str = "line",
               pos: str = "top-right") -> None:
        if not items:
            return
        t = self.theme
        max_len = max(len(lab) for lab, _ in items)
        box_w = min(180, 28 + max_len * 7.2)
        box_h = 8 + len(items) * 18
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
            iy = by + 14 + i * 18
            if kind == "line":
                self._parts.append(
                    f'<line x1="{bx + 8}" y1="{iy}" x2="{bx + 24}" y2="{iy}" '
                    f'stroke="{color}" stroke-width="2.5" stroke-linecap="round"/>'
                )
                self._parts.append(
                    f'<circle cx="{bx + 16}" cy="{iy}" r="3" fill="{color}"/>'
                )
            elif kind == "bar":
                self._parts.append(
                    f'<rect x="{bx + 8}" y="{iy - 5}" width="16" height="10" '
                    f'rx="2" fill="{color}"/>'
                )
            else:
                self._parts.append(
                    f'<circle cx="{bx + 16}" cy="{iy}" r="4" fill="{color}"/>'
                )
            self._parts.append(
                f'<text x="{bx + 30}" y="{iy + 4}" font-family="{t["font"]}" '
                f'font-size="11" fill="{t["fg"]}">{utils.escape_xml(lab)}</text>'
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
    ) -> None:
        # break lines on NaN gaps
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

        dash = ' stroke-dasharray="6,4"' if dashed else ""
        all_pts: list[tuple[float, float]] = []
        for pts in segs:
            if len(pts) == 1:
                self._parts.append(
                    f'<circle cx="{pts[0][0]:.2f}" cy="{pts[0][1]:.2f}" r="4" fill="{color}" '
                    f'clip-path="url(#{self._clip_id})"/>'
                )
                all_pts.extend(pts)
                continue
            if len(pts) < 2:
                continue
            d = "M " + " L ".join(f"{px:.2f},{py:.2f}" for px, py in pts)
            self._parts.append(
                f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
                f'stroke-linecap="round" stroke-linejoin="round"{dash} '
                f'clip-path="url(#{self._clip_id})"/>'
            )
            all_pts.extend(pts)

        if markers and 0 < len(all_pts) <= 80:
            for px, py in all_pts:
                self._parts.append(
                    f'<circle cx="{px:.2f}" cy="{py:.2f}" r="3.5" fill="{color}" '
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
        pts = self._valid_pts(xs, ys, x0, x1, y0, y1)
        if len(pts) < 2:
            return
        baseline_y = 0.0 if y0 <= 0 <= y1 else y0
        baseline = self._sy(baseline_y, y0, y1)
        d = "M " + " L ".join(f"{px:.2f},{py:.2f}" for px, py in pts)
        d += f" L {pts[-1][0]:.2f},{baseline:.2f} L {pts[0][0]:.2f},{baseline:.2f} Z"
        self._parts.append(
            f'<path d="{d}" fill="{color}" fill-opacity="{opacity}" '
            f'stroke="none" clip-path="url(#{self._clip_id})"/>'
        )
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
        for x, y in zip(xs, ys):
            if (
                not isinstance(x, (int, float))
                or not isinstance(y, (int, float))
                or not math.isfinite(float(x))
                or not math.isfinite(float(y))
            ):
                continue
            sx, sy = self._sx(float(x), x0, x1), self._sy(float(y), y0, y1)
            self._parts.append(
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
                self._parts.append(
                    f'<text x="{x + bar_w/2:.2f}" y="{ty:.2f}" text-anchor="middle" '
                    f'font-family="{t["font"]}" font-size="10" fill="{t["muted"]}">'
                    f"{utils.escape_xml(utils.format_number(val))}</text>"
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
        self._parts.append(
            f'<text x="{self.width / 2}" y="44" text-anchor="middle" '
            f'font-family="{t["font"]}" font-size="12" '
            f'fill="{t["muted"]}">{utils.escape_xml(text)}</text>'
        )

    def footnote(self, text: str) -> None:
        if not text:
            return
        t = self.theme
        self._parts.append(
            f'<text x="{self.margin["left"]}" y="{self.height - 6}" text-anchor="start" '
            f'font-family="{t["font"]}" font-size="10" '
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
                 text: str, color: str | None = None, anchor: str = "start") -> None:
        t = self.theme
        sx, sy = self._sx(x, x0, x1), self._sy(y, y0, y1)
        col = color or t["fg"]
        self._parts.append(
            f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="3" fill="{col}" '
            f'clip-path="url(#{self._clip_id})"/>'
        )
        self._parts.append(
            f'<text x="{sx + 6:.2f}" y="{sy - 6:.2f}" text-anchor="{anchor}" '
            f'font-family="{t["font"]}" font-size="11" fill="{col}" '
            f'clip-path="url(#{self._clip_id})">{utils.escape_xml(text)}</text>'
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
            base = 0.0 if y0 <= 0 <= y1 else y0
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
                y_top = self._sy(base + val, y0, y1)
                y_bot = self._sy(base, y0, y1)
                top = min(y_top, y_bot)
                h = max(abs(y_bot - y_top), 0.5)
                self._parts.append(
                    f'<rect x="{x:.2f}" y="{top:.2f}" width="{bar_w:.2f}" height="{h:.2f}" '
                    f'rx="2" fill="{color}" clip-path="url(#{self._clip_id})"/>'
                )
                base += val

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
