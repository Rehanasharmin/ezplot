"""
Fast pure-Python raster canvas + PNG writer (stdlib only).

Hot paths use bulk row writes (memoryview / slice assigns) instead of
per-pixel Python loops. JPEG/WebP still use Pillow when installed.
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path
from typing import Sequence

from . import font
from . import utils
from .style import get_theme

# ---------------------------------------------------------------------------
# color helpers
# ---------------------------------------------------------------------------

_NAMED = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (239, 68, 68),
    "green": (34, 197, 94),
    "blue": (59, 130, 246),
    "yellow": (234, 179, 8),
    "orange": (249, 115, 22),
    "purple": (168, 85, 247),
    "pink": (236, 72, 153),
    "cyan": (6, 182, 212),
    "coral": (255, 127, 80),
    "gray": (156, 163, 175),
    "grey": (156, 163, 175),
    "transparent": (0, 0, 0),
}

# cache parsed CSS colors
_COLOR_CACHE: dict[str, tuple[int, int, int]] = {}


def parse_color(
    c: str | Sequence[int] | None,
    default: tuple[int, int, int] = (0, 0, 0),
) -> tuple[int, int, int]:
    if c is None:
        return default
    if isinstance(c, tuple) and len(c) >= 3 and isinstance(c[0], int):
        return c[0] & 255, c[1] & 255, c[2] & 255
    if isinstance(c, (list, tuple)) and len(c) >= 3:
        return int(c[0]) & 255, int(c[1]) & 255, int(c[2]) & 255
    s = str(c).strip().lower()
    hit = _COLOR_CACHE.get(s)
    if hit is not None:
        return hit
    if s in _NAMED:
        _COLOR_CACHE[s] = _NAMED[s]
        return _NAMED[s]
    out = default
    if s.startswith("#"):
        h = s[1:]
        if len(h) == 3:
            h = h[0] * 2 + h[1] * 2 + h[2] * 2
        if len(h) >= 6:
            try:
                out = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            except ValueError:
                out = default
    elif s.startswith("rgb"):
        try:
            inside = s[s.index("(") + 1 : s.rindex(")")]
            parts = inside.split(",")
            out = (int(float(parts[0])), int(float(parts[1])), int(float(parts[2])))
        except Exception:
            out = default
    _COLOR_CACHE[s] = out
    return out


# ---------------------------------------------------------------------------
# canvas — bytearray RGB, bulk row ops
# ---------------------------------------------------------------------------

class Canvas:
    """RGB24 framebuffer optimized for bulk writes."""

    __slots__ = ("w", "h", "buf", "row")

    def __init__(self, width: int, height: int, bg: tuple[int, int, int] = (255, 255, 255)):
        self.w = max(1, int(width))
        self.h = max(1, int(height))
        n = self.w * self.h * 3
        r, g, b = bg
        # build one row then multiply — much faster than per-pixel
        row = bytes((r, g, b)) * self.w
        self.buf = bytearray(row * self.h)
        self.row = self.w * 3  # bytes per row

    def fill(self, color: tuple[int, int, int]) -> None:
        r, g, b = color
        row = bytes((r, g, b)) * self.w
        self.buf[:] = row * self.h

    def put(self, x: int, y: int, color: tuple[int, int, int], a: float = 1.0) -> None:
        if x < 0 or y < 0 or x >= self.w or y >= self.h:
            return
        i = y * self.row + x * 3
        if a >= 0.999:
            self.buf[i] = color[0]
            self.buf[i + 1] = color[1]
            self.buf[i + 2] = color[2]
        elif a > 0.001:
            inv = 1.0 - a
            self.buf[i] = int(self.buf[i] * inv + color[0] * a + 0.5)
            self.buf[i + 1] = int(self.buf[i + 1] * inv + color[1] * a + 0.5)
            self.buf[i + 2] = int(self.buf[i + 2] * inv + color[2] * a + 0.5)

    def _row_span_opaque(self, y: int, x0: int, x1: int, color: tuple[int, int, int]) -> None:
        """Fill [x0, x1) on row y with solid color — one slice assign."""
        if y < 0 or y >= self.h or x0 >= x1:
            return
        if x0 < 0:
            x0 = 0
        if x1 > self.w:
            x1 = self.w
        if x0 >= x1:
            return
        r, g, b = color
        start = y * self.row + x0 * 3
        n = x1 - x0
        self.buf[start : start + n * 3] = bytes((r, g, b)) * n

    def _row_span_alpha(self, y: int, x0: int, x1: int, color: tuple[int, int, int], a: float) -> None:
        if y < 0 or y >= self.h or x0 >= x1 or a <= 0.001:
            return
        if x0 < 0:
            x0 = 0
        if x1 > self.w:
            x1 = self.w
        if x0 >= x1:
            return
        if a >= 0.999:
            self._row_span_opaque(y, x0, x1, color)
            return
        inv = 1.0 - a
        r, g, b = color
        fr, fg, fb = r * a, g * a, b * a
        base = y * self.row + x0 * 3
        buf = self.buf
        for i in range(x1 - x0):
            j = base + i * 3
            buf[j] = int(buf[j] * inv + fr + 0.5)
            buf[j + 1] = int(buf[j + 1] * inv + fg + 0.5)
            buf[j + 2] = int(buf[j + 2] * inv + fb + 0.5)

    def hline(self, x0: int, x1: int, y: int, color: tuple[int, int, int], a: float = 1.0) -> None:
        if x0 > x1:
            x0, x1 = x1, x0
        if a >= 0.999:
            self._row_span_opaque(y, x0, x1 + 1, color)
        else:
            self._row_span_alpha(y, x0, x1 + 1, color, a)

    def vline(self, x: int, y0: int, y1: int, color: tuple[int, int, int], a: float = 1.0) -> None:
        if x < 0 or x >= self.w:
            return
        if y0 > y1:
            y0, y1 = y1, y0
        if y0 < 0:
            y0 = 0
        if y1 >= self.h:
            y1 = self.h - 1
        r, g, b = color
        row = self.row
        buf = self.buf
        if a >= 0.999:
            for y in range(y0, y1 + 1):
                i = y * row + x * 3
                buf[i] = r
                buf[i + 1] = g
                buf[i + 2] = b
        elif a > 0.001:
            inv = 1.0 - a
            fr, fg, fb = r * a, g * a, b * a
            for y in range(y0, y1 + 1):
                i = y * row + x * 3
                buf[i] = int(buf[i] * inv + fr + 0.5)
                buf[i + 1] = int(buf[i + 1] * inv + fg + 0.5)
                buf[i + 2] = int(buf[i + 2] * inv + fb + 0.5)

    def line(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        color: tuple[int, int, int],
        width: float = 1.0,
        a: float = 1.0,
    ) -> None:
        # thin solid line → Bresenham (very fast)
        if width <= 1.5 and a >= 0.999:
            self._bresenham(int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1)), color)
            return
        dx = x1 - x0
        dy = y1 - y0
        dist = math.hypot(dx, dy)
        if dist < 1e-9:
            self.dot(x0, y0, max(1.0, width * 0.5), color, a)
            return
        half = max(0.5, width * 0.5)
        # step ~1px along the line
        steps = max(1, int(dist + 0.5))
        inv = 1.0 / steps
        # for moderate thickness use small stamps
        if half <= 2.0:
            for i in range(steps + 1):
                t = i * inv
                self.dot(x0 + dx * t, y0 + dy * t, half, color, a)
        else:
            # thick: draw as capsule of circles less frequently
            step = max(1, int(half))
            for i in range(0, steps + 1, step):
                t = i * inv
                self.dot(x0 + dx * t, y0 + dy * t, half, color, a)
            self.dot(x1, y1, half, color, a)

    def _bresenham(self, x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int]) -> None:
        r, g, b = color
        buf = self.buf
        row = self.row
        w, h = self.w, self.h
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            if 0 <= x0 < w and 0 <= y0 < h:
                i = y0 * row + x0 * 3
                buf[i] = r
                buf[i + 1] = g
                buf[i + 2] = b
            if x0 == x1 and y0 == y1:
                break
            e2 = err << 1
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def polyline(
        self,
        pts: Sequence[tuple[float, float]],
        color: tuple[int, int, int],
        width: float = 2.0,
        a: float = 1.0,
    ) -> None:
        for i in range(len(pts) - 1):
            self.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], color, width, a)

    def dot(self, cx: float, cy: float, r: float, color: tuple[int, int, int], a: float = 1.0) -> None:
        if r < 0.6:
            self.put(int(cx + 0.5), int(cy + 0.5), color, a)
            return
        r2 = r * r
        x0 = max(0, int(cx - r))
        x1 = min(self.w - 1, int(cx + r + 1))
        y0 = max(0, int(cy - r))
        y1 = min(self.h - 1, int(cy + r + 1))
        # scanline circle — for each row compute x span
        opaque = a >= 0.999
        for y in range(y0, y1 + 1):
            dy = (y + 0.5) - cy
            rem = r2 - dy * dy
            if rem < 0:
                continue
            half = math.sqrt(rem)
            xa = max(x0, int(cx - half + 0.5))
            xb = min(x1 + 1, int(cx + half + 0.5) + 1)
            if opaque:
                self._row_span_opaque(y, xa, xb, color)
            else:
                self._row_span_alpha(y, xa, xb, color, a)

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        color: tuple[int, int, int],
        a: float = 1.0,
        radius: float = 0.0,
    ) -> None:
        if w <= 0 or h <= 0:
            return
        x0 = int(math.floor(x))
        y0 = int(math.floor(y))
        x1 = int(math.ceil(x + w))
        y1 = int(math.ceil(y + h))
        if x0 < 0:
            x0 = 0
        if y0 < 0:
            y0 = 0
        if x1 > self.w:
            x1 = self.w
        if y1 > self.h:
            y1 = self.h
        if x0 >= x1 or y0 >= y1:
            return

        rad = max(0.0, min(radius, w * 0.5, h * 0.5))
        opaque = a >= 0.999

        # fast path: sharp rect
        if rad < 1.0:
            if opaque:
                for yy in range(y0, y1):
                    self._row_span_opaque(yy, x0, x1, color)
            else:
                for yy in range(y0, y1):
                    self._row_span_alpha(yy, x0, x1, color, a)
            return

        # rounded: middle band solid, corners as circle quarters
        ri = int(rad)
        # middle body (full width)
        ym0 = min(y1, y0 + ri)
        ym1 = max(y0, y1 - ri)
        if opaque:
            for yy in range(ym0, ym1):
                self._row_span_opaque(yy, x0, x1, color)
        else:
            for yy in range(ym0, ym1):
                self._row_span_alpha(yy, x0, x1, color, a)

        # top & bottom strips with rounded ends
        cx_l = x + rad
        cx_r = x + w - rad
        cy_t = y + rad
        cy_b = y + h - rad
        r2 = rad * rad
        for yy in range(y0, ym0):
            dy = (yy + 0.5) - cy_t
            rem = r2 - dy * dy
            if rem < 0:
                continue
            half = math.sqrt(rem)
            xa = max(x0, int(cx_l - half + 0.5))
            xb = min(x1, int(cx_r + half + 0.5) + 1)
            if opaque:
                self._row_span_opaque(yy, xa, xb, color)
            else:
                self._row_span_alpha(yy, xa, xb, color, a)
        for yy in range(ym1, y1):
            dy = (yy + 0.5) - cy_b
            rem = r2 - dy * dy
            if rem < 0:
                continue
            half = math.sqrt(rem)
            xa = max(x0, int(cx_l - half + 0.5))
            xb = min(x1, int(cx_r + half + 0.5) + 1)
            if opaque:
                self._row_span_opaque(yy, xa, xb, color)
            else:
                self._row_span_alpha(yy, xa, xb, color, a)

    def fill_poly(
        self,
        pts: Sequence[tuple[float, float]],
        color: tuple[int, int, int],
        a: float = 1.0,
    ) -> None:
        n = len(pts)
        if n < 3:
            return
        ys = [p[1] for p in pts]
        y0 = max(0, int(math.floor(min(ys))))
        y1 = min(self.h - 1, int(math.ceil(max(ys))))
        # pre-build edges
        edges = []
        for i in range(n):
            x1, y1_ = pts[i]
            x2, y2_ = pts[(i + 1) % n]
            if y1_ == y2_:
                continue
            if y1_ > y2_:
                x1, y1_, x2, y2_ = x2, y2_, x1, y1_
            edges.append((y1_, y2_, x1, x2))
        if not edges:
            return
        opaque = a >= 0.999
        for y in range(y0, y1 + 1):
            scan = y + 0.5
            xs: list[float] = []
            for ey0, ey1, ex0, ex1 in edges:
                if ey0 <= scan < ey1:
                    t = (scan - ey0) / (ey1 - ey0)
                    xs.append(ex0 + t * (ex1 - ex0))
            if len(xs) < 2:
                continue
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                xa = max(0, int(math.floor(xs[i])))
                xb = min(self.w, int(math.ceil(xs[i + 1])))
                if opaque:
                    self._row_span_opaque(y, xa, xb, color)
                else:
                    self._row_span_alpha(y, xa, xb, color, a)

    def text(
        self,
        x: float,
        y: float,
        text: str,
        color: tuple[int, int, int],
        scale: int = 1,
        align: str = "left",
        a: float = 1.0,
    ) -> None:
        if not text:
            return
        text = (
            str(text)
            .replace("…", "...")
            .replace("—", "-")
            .replace("–", "-")
            .replace("×", "x")
        )
        scale = 1 if scale < 1 else int(scale)
        tw = font.text_width(text, scale)
        if align == "center":
            x -= tw * 0.5
        elif align in ("end", "right"):
            x -= tw
        x0 = int(x + 0.5)
        y0 = int(y + 0.5)
        # fast opaque text path
        if a >= 0.999:
            r, g, b = color
            buf = self.buf
            row = self.row
            w, h = self.w, self.h
            for dx, dy in font.iter_pixels(text, scale):
                px, py = x0 + dx, y0 + dy
                if 0 <= px < w and 0 <= py < h:
                    i = py * row + px * 3
                    buf[i] = r
                    buf[i + 1] = g
                    buf[i + 2] = b
        else:
            for dx, dy in font.iter_pixels(text, scale):
                self.put(x0 + dx, y0 + dy, color, a)

    def to_png_bytes(self) -> bytes:
        return write_png(self.w, self.h, self.buf)

    def save_png(self, path: str | Path) -> Path:
        path = Path(path)
        path.write_bytes(self.to_png_bytes())
        return path

    def to_pil(self):
        from PIL import Image  # type: ignore

        return Image.frombytes("RGB", (self.w, self.h), bytes(self.buf))

    def save(self, path: str | Path, quality: int = 90) -> Path:
        path = Path(path)
        ext = path.suffix.lower()
        if ext in ("", ".png"):
            if not ext:
                path = path.with_suffix(".png")
            return self.save_png(path)
        if ext in {".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif"}:
            try:
                img = self.to_pil()
            except ImportError as e:
                raise RuntimeError(
                    f"Saving {ext} needs Pillow. Install with: pip install pillow\n"
                    f"(PNG always works with zero dependencies.)"
                ) from e
            path.parent.mkdir(parents=True, exist_ok=True)
            kw = {}
            if ext in {".jpg", ".jpeg", ".webp"}:
                kw["quality"] = int(quality)
                if ext in {".jpg", ".jpeg"}:
                    kw["optimize"] = False  # faster
                    kw["subsampling"] = 2
            img.save(str(path), **kw)
            return path
        return self.save_png(path.with_suffix(".png"))


def write_png(width: int, height: int, rgb: bytearray | bytes) -> bytes:
    """Encode RGB24 as PNG — filter-0 rows, zlib level 1 (fast)."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    row_bytes = width * 3
    # pre-size: 1 filter byte + RGB per row
    raw = bytearray((row_bytes + 1) * height)
    mv_src = memoryview(rgb)
    for y in range(height):
        dest = y * (row_bytes + 1)
        raw[dest] = 0  # filter None
        s = y * row_bytes
        raw[dest + 1 : dest + 1 + row_bytes] = mv_src[s : s + row_bytes]

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    # level 1 = much faster, still fine for charts
    compressed = zlib.compress(raw, 1)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")


# ---------------------------------------------------------------------------
# chart → raster
# ---------------------------------------------------------------------------

class RasterRenderer:
    """Draw charts into a Canvas (same geometry as SVGRenderer)."""

    __slots__ = (
        "width", "height", "theme", "margin", "cv",
        "_bg", "_fg", "_grid", "_axis", "_title_c", "_muted",
        "_ml", "_mt", "_pw", "_ph",
    )

    def __init__(self, width: int = 720, height: int = 420, theme: str | None = None):
        self.width = max(120, int(width))
        self.height = max(100, int(height))
        self.theme = get_theme(theme)
        self.margin = {"top": 48, "right": 28, "bottom": 56, "left": 64}
        bg = parse_color(self.theme["bg"], (255, 255, 255))
        self.cv = Canvas(self.width, self.height, bg)
        self._bg = bg
        self._fg = parse_color(self.theme["fg"])
        self._grid = parse_color(self.theme["grid"])
        self._axis = parse_color(self.theme["axis"])
        self._title_c = parse_color(self.theme["title"])
        self._muted = parse_color(self.theme["muted"])
        self._ml = self.margin["left"]
        self._mt = self.margin["top"]
        self._pw = float(self.width - self.margin["left"] - self.margin["right"])
        self._ph = float(self.height - self.margin["top"] - self.margin["bottom"])

    def _sync_geom(self) -> None:
        self._ml = self.margin["left"]
        self._mt = self.margin["top"]
        self._pw = max(10.0, float(self.width - self.margin["left"] - self.margin["right"]))
        self._ph = max(10.0, float(self.height - self.margin["top"] - self.margin["bottom"]))

    @property
    def plot_w(self) -> float:
        return max(10.0, self.width - self.margin["left"] - self.margin["right"])

    @property
    def plot_h(self) -> float:
        return max(10.0, self.height - self.margin["top"] - self.margin["bottom"])

    def _sx(self, x: float, x0: float, x1: float) -> float:
        if x1 == x0 or not math.isfinite(x):
            return self._ml + self._pw * 0.5
        return self._ml + (x - x0) / (x1 - x0) * self._pw

    def _sy(self, y: float, y0: float, y1: float) -> float:
        if y1 == y0 or not math.isfinite(y):
            return self._mt + self._ph * 0.5
        return self._mt + (1.0 - (y - y0) / (y1 - y0)) * self._ph

    def title(self, text: str) -> None:
        if text:
            self.cv.text(self.width * 0.5, 16, text, self._title_c, scale=2, align="center")

    def xlabel(self, text: str) -> None:
        if text:
            self._sync_geom()
            self.cv.text(
                self._ml + self._pw * 0.5,
                self.height - 18,
                text,
                self._muted,
                scale=1,
                align="center",
            )

    def ylabel(self, text: str) -> None:
        if not text:
            return
        self._sync_geom()
        th = font.text_height(1)
        total = len(text) * (th + 1)
        x = 8
        y = self._mt + self._ph * 0.5 - total * 0.5
        for i, ch in enumerate(text):
            self.cv.text(x, y + i * (th + 1), ch, self._muted, scale=1)

    def empty_message(self, msg: str = "No data") -> None:
        self.cv.text(self.width * 0.5, self.height * 0.5, msg, self._muted, scale=2, align="center")

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
    ) -> None:
        self._sync_geom()
        xt = xticks if xticks is not None else utils.nice_ticks(x0, x1)
        yt = yticks if yticks is not None else utils.nice_ticks(y0, y1)
        yt = [v for v in yt if y0 - 1e-12 <= v <= y1 + 1e-12] or [y0, y1]
        if not categorical_x:
            xt = [v for v in xt if x0 - 1e-12 <= v <= x1 + 1e-12] or [x0, x1]

        left = int(self._ml)
        top = int(self._mt)
        bottom = int(self._mt + self._ph)
        right = int(self._ml + self._pw)

        if grid:
            # solid light grid lines (faster than dashed put loops)
            for y in yt:
                sy = int(self._sy(y, y0, y1) + 0.5)
                self.cv.hline(left, right, sy, self._grid)
            if not categorical_x:
                for x in xt:
                    sx = int(self._sx(x, x0, x1) + 0.5)
                    self.cv.vline(sx, top, bottom, self._grid)

        self.cv.hline(left, right, bottom, self._axis)
        self.cv.vline(left, top, bottom, self._axis)

        for y in yt:
            sy = int(self._sy(y, y0, y1) + 0.5)
            self.cv.hline(left - 4, left, sy, self._axis)
            self.cv.text(left - 8, sy - 3, utils.format_number(y), self._muted, scale=1, align="end")

        if categorical_x and xlabels is not None:
            n = len(xlabels)
            for i, lab in enumerate(xlabels):
                sx = self._sx(i + 0.5, 0, n) if n else left
                self.cv.vline(int(sx), bottom, bottom + 4, self._axis)
                self.cv.text(sx, bottom + 8, utils.truncate_label(str(lab), 12), self._muted, scale=1, align="center")
        else:
            for x in xt:
                sx = int(self._sx(x, x0, x1) + 0.5)
                self.cv.vline(sx, bottom, bottom + 4, self._axis)
                self.cv.text(sx, bottom + 8, utils.format_number(x), self._muted, scale=1, align="center")

    def legend(self, items: list[tuple[str, str]], kind: str = "line",
               pos: str = "top-right") -> None:
        if not items:
            return
        self._sync_geom()
        max_len = max(len(lab) for lab, _ in items)
        box_w = min(180, 28 + max_len * 6)
        box_h = 8 + len(items) * 16
        if pos in ("top-left", "tl"):
            bx, by = int(self._ml + 4), int(self._mt + 6)
        elif pos in ("bottom-left", "bl"):
            bx, by = int(self._ml + 4), int(self._mt + self._ph - box_h - 6)
        elif pos in ("bottom-right", "br"):
            bx = int(self._ml + self._pw - box_w - 4)
            by = int(self._mt + self._ph - box_h - 6)
        else:
            bx = int(self._ml + self._pw - box_w - 4)
            by = int(self._mt + 6)
        self.cv.rect(bx, by, box_w, box_h, self._bg, a=0.92, radius=4)
        self.cv.hline(bx, bx + box_w, by, self._grid)
        self.cv.hline(bx, bx + box_w, by + box_h, self._grid)
        self.cv.vline(bx, by, by + box_h, self._grid)
        self.cv.vline(bx + box_w, by, by + box_h, self._grid)
        for i, (lab, color) in enumerate(items):
            iy = by + 10 + i * 16
            col = parse_color(color)
            if kind == "bar":
                self.cv.rect(bx + 8, iy - 4, 14, 8, col, radius=2)
            else:
                self.cv.line(bx + 8, iy, bx + 22, iy, col, width=2.0)
                self.cv.dot(bx + 15, iy, 2.5, col)
            self.cv.text(bx + 28, iy - 3, lab, self._fg, scale=1)

    def line_series(self, xs, ys, x0, x1, y0, y1, color, width=2.5, markers=True):
        self._sync_geom()
        col = parse_color(color)
        segs: list[list[tuple[float, float]]] = [[]]
        sx = self._sx
        sy = self._sy
        for x, y in zip(xs, ys):
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                if segs[-1]:
                    segs.append([])
                continue
            fx, fy = float(x), float(y)
            if not math.isfinite(fx) or not math.isfinite(fy):
                if segs[-1]:
                    segs.append([])
                continue
            segs[-1].append((sx(fx, x0, x1), sy(fy, y0, y1)))
        all_pts: list[tuple[float, float]] = []
        for pts in segs:
            if len(pts) == 1:
                self.cv.dot(pts[0][0], pts[0][1], 3.5, col)
                all_pts.extend(pts)
            elif len(pts) >= 2:
                self.cv.polyline(pts, col, width=width)
                all_pts.extend(pts)
        if markers and 0 < len(all_pts) <= 80:
            bg = self._bg
            for px, py in all_pts:
                self.cv.dot(px, py, 3.0, col)
                self.cv.dot(px, py, 1.4, bg)

    def area_series(self, xs, ys, x0, x1, y0, y1, color, opacity=0.25):
        self._sync_geom()
        col = parse_color(color)
        pts = []
        sx, sy = self._sx, self._sy
        for x, y in zip(xs, ys):
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                fx, fy = float(x), float(y)
                if math.isfinite(fx) and math.isfinite(fy):
                    pts.append((sx(fx, x0, x1), sy(fy, y0, y1)))
        if len(pts) < 2:
            return
        base = sy(0.0 if y0 <= 0 <= y1 else y0, y0, y1)
        self.cv.fill_poly(pts + [(pts[-1][0], base), (pts[0][0], base)], col, a=opacity)
        self.line_series(xs, ys, x0, x1, y0, y1, color, width=2, markers=False)

    def scatter_series(self, xs, ys, x0, x1, y0, y1, color, size=5, alpha=0.85):
        self._sync_geom()
        col = parse_color(color)
        sx, sy = self._sx, self._sy
        for x, y in zip(xs, ys):
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                fx, fy = float(x), float(y)
                if math.isfinite(fx) and math.isfinite(fy):
                    self.cv.dot(sx(fx, x0, x1), sy(fy, y0, y1), size, col, a=alpha)

    def bars_v(self, n, values, y0, y1, colors, gap=0.28, group=0, n_groups=1, show_values=False):
        if n <= 0:
            return
        self._sync_geom()
        band = self._pw / n
        gap = 0.0 if gap < 0 else (0.8 if gap > 0.8 else gap)
        if n_groups > 1:
            bar_w = max(1.0, band * (1 - gap) / n_groups)
            offset = group * bar_w
            left_pad = band * gap * 0.5
        else:
            bar_w = max(1.0, band * (1 - gap))
            offset = 0.0
            left_pad = band * gap * 0.5
        base_val = 0.0 if y0 <= 0 <= y1 else y0
        y_base = self._sy(base_val, y0, y1)
        n_colors = len(colors) or 1
        for i, val in enumerate(values):
            if i >= n or not isinstance(val, (int, float)):
                continue
            fv = float(val)
            if not math.isfinite(fv):
                continue
            col = parse_color(colors[i % n_colors] if n_groups == 1 else colors[group % n_colors])
            x = self._ml + i * band + left_pad + offset
            y_top = self._sy(fv, y0, y1)
            top = y_top if y_top < y_base else y_base
            h = abs(y_base - y_top)
            if h < 0.5:
                h = 0.5
            self.cv.rect(x, top, bar_w, h, col, radius=3)
            if show_values and bar_w >= 14:
                ty = top - 10 if fv >= base_val else top + h + 2
                self.cv.text(x + bar_w * 0.5, ty, utils.format_number(fv), self._muted, scale=1, align="center")

    def bars_h(self, n, values, x0, x1, colors, categories, gap=0.28):
        if n <= 0:
            return
        self._sync_geom()
        band = self._ph / n
        bar_h = max(1.0, band * (1 - gap))
        base_val = 0.0 if x0 <= 0 <= x1 else x0
        x_base = self._sx(base_val, x0, x1)
        n_colors = len(colors) or 1
        for i, val in enumerate(values):
            if i >= n or not isinstance(val, (int, float)):
                continue
            fv = float(val)
            if not math.isfinite(fv):
                continue
            col = parse_color(colors[i % n_colors])
            y = self._mt + i * band + band * gap * 0.5
            x_end = self._sx(fv, x0, x1)
            left = x_base if x_base < x_end else x_end
            w = abs(x_end - x_base)
            if w < 0.5:
                w = 0.5
            self.cv.rect(left, y, w, bar_h, col, radius=3)
            lab = utils.truncate_label(categories[i] if i < len(categories) else str(i), 12)
            self.cv.text(self._ml - 8, y + bar_h * 0.5 - 3, lab, self._muted, scale=1, align="end")


    def subtitle(self, text: str) -> None:
        if text:
            self.cv.text(self.width * 0.5, 34, text, self._muted, scale=1, align="center")

    def footnote(self, text: str) -> None:
        if text:
            self._sync_geom()
            self.cv.text(self._ml, self.height - 10, text, self._muted, scale=1, align="left")

    def hline(self, y, y0, y1, color, dashed=True, width=1.5):
        self._sync_geom()
        from .raster import parse_color as _pc
        col = _pc(color)
        sy = int(self._sy(float(y), y0, y1) + 0.5)
        left, right = int(self._ml), int(self._ml + self._pw)
        if dashed:
            for x in range(left, right, 8):
                self.cv.hline(x, min(x + 4, right), sy, col)
        else:
            self.cv.hline(left, right, sy, col)

    def vline(self, x, x0, x1, color, dashed=True, width=1.5):
        self._sync_geom()
        from .raster import parse_color as _pc
        col = _pc(color)
        sx = int(self._sx(float(x), x0, x1) + 0.5)
        top, bot = int(self._mt), int(self._mt + self._ph)
        if dashed:
            for y in range(top, bot, 8):
                self.cv.vline(sx, y, min(y + 4, bot), col)
        else:
            self.cv.vline(sx, top, bot, col)

    def annotate(self, x, y, x0, x1, y0, y1, text, color=None, anchor="start"):
        self._sync_geom()
        from .raster import parse_color as _pc
        col = _pc(color or self.theme.get("fg"))
        sx, sy = self._sx(float(x), x0, x1), self._sy(float(y), y0, y1)
        self.cv.dot(sx, sy, 3, col)
        align = "left" if anchor in ("start", "left") else ("end" if anchor in ("end", "right") else "center")
        self.cv.text(sx + 6, sy - 8, str(text), col, scale=1, align=align)

    def bars_stacked(self, n, series_values, y0, y1, colors, gap=0.28):
        if n <= 0 or not series_values:
            return
        self._sync_geom()
        from .raster import parse_color as _pc
        band = self._pw / n
        bar_w = max(1.0, band * (1 - gap))
        left_pad = band * gap * 0.5
        for i in range(n):
            base = 0.0 if y0 <= 0 <= y1 else y0
            for si, vals in enumerate(series_values):
                if i >= len(vals):
                    continue
                val = vals[i]
                if not isinstance(val, (int, float)):
                    continue
                fv = float(val)
                if not math.isfinite(fv) or fv == 0:
                    continue
                col = _pc(colors[si % len(colors)])
                x = self._ml + i * band + left_pad
                y_top = self._sy(base + fv, y0, y1)
                y_bot = self._sy(base, y0, y1)
                top = y_top if y_top < y_bot else y_bot
                h = abs(y_bot - y_top)
                if h < 0.5:
                    h = 0.5
                self.cv.rect(x, top, bar_w, h, col, radius=2)
                base += fv

    def pie(self, values, labels, colors, donut=False):
        self._sync_geom()
        clean = []
        for i, v in enumerate(values):
            if isinstance(v, (int, float)):
                fv = float(v)
                if math.isfinite(fv) and fv > 0:
                    clean.append((i, fv))
        total = sum(v for _, v in clean)
        if total <= 0:
            self.empty_message("No positive values")
            return
        cx = self.width * 0.5
        cy = self._mt + self._ph * 0.5
        r = min(self._pw, self._ph) * 0.36
        inner = r * 0.55 if donut else 0.0
        angle = -math.pi / 2
        n_colors = len(colors) or 1
        for i, val in clean:
            sweep = 2 * math.pi * (val / total)
            col = parse_color(colors[i % n_colors])
            # fewer steps for small slices
            steps = max(6, min(48, int(sweep / (math.pi / 24)) + 1))
            pts = [(cx, cy)]
            for s in range(steps + 1):
                a = angle + sweep * (s / steps)
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
            self.cv.fill_poly(pts, col)
            mid = angle + sweep * 0.5
            pct = val / total * 100
            if pct >= 3 or len(clean) <= 6:
                lr = r * 1.15
                lx = cx + lr * math.cos(mid)
                ly = cy + lr * math.sin(mid)
                lab = labels[i] if i < len(labels) else f"#{i+1}"
                anchor = "left" if math.cos(mid) >= 0 else "end"
                self.cv.text(lx, ly - 3, f"{lab} ({pct:.0f}%)", self._fg, scale=1, align=anchor)
            angle += sweep
        if donut and inner > 0:
            self.cv.dot(cx, cy, inner, self._bg)
