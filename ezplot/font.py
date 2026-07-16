"""Tiny 5×7 bitmap font with precomputed pixel caches (fast text)."""

from __future__ import annotations

_H = 7
_W = 5

_GLYPHS: dict[str, tuple[int, ...]] = {
    " ": (0, 0, 0, 0, 0, 0, 0),
    "!": (4, 4, 4, 4, 0, 4, 0),
    '"': (10, 10, 10, 0, 0, 0, 0),
    "#": (10, 31, 10, 10, 31, 10, 0),
    "$": (4, 15, 20, 14, 5, 30, 4),
    "%": (25, 25, 2, 4, 8, 19, 19),
    "&": (8, 20, 20, 8, 21, 18, 13),
    "'": (4, 4, 4, 0, 0, 0, 0),
    "(": (2, 4, 8, 8, 8, 4, 2),
    ")": (8, 4, 2, 2, 2, 4, 8),
    "*": (0, 4, 21, 14, 21, 4, 0),
    "+": (0, 4, 4, 31, 4, 4, 0),
    ",": (0, 0, 0, 0, 4, 4, 8),
    "-": (0, 0, 0, 31, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 4, 0),
    "/": (1, 1, 2, 4, 8, 16, 16),
    "0": (14, 17, 19, 21, 25, 17, 14),
    "1": (4, 12, 4, 4, 4, 4, 14),
    "2": (14, 17, 1, 2, 4, 8, 31),
    "3": (14, 17, 1, 6, 1, 17, 14),
    "4": (2, 6, 10, 18, 31, 2, 2),
    "5": (31, 16, 30, 1, 1, 17, 14),
    "6": (6, 8, 16, 30, 17, 17, 14),
    "7": (31, 1, 2, 4, 8, 8, 8),
    "8": (14, 17, 17, 14, 17, 17, 14),
    "9": (14, 17, 17, 15, 1, 2, 12),
    ":": (0, 4, 0, 0, 4, 0, 0),
    ";": (0, 4, 0, 0, 4, 4, 8),
    "<": (2, 4, 8, 16, 8, 4, 2),
    "=": (0, 0, 31, 0, 31, 0, 0),
    ">": (8, 4, 2, 1, 2, 4, 8),
    "?": (14, 17, 1, 2, 4, 0, 4),
    "@": (14, 17, 1, 13, 21, 21, 14),
    "A": (14, 17, 17, 31, 17, 17, 17),
    "B": (30, 17, 17, 30, 17, 17, 30),
    "C": (14, 17, 16, 16, 16, 17, 14),
    "D": (30, 17, 17, 17, 17, 17, 30),
    "E": (31, 16, 16, 30, 16, 16, 31),
    "F": (31, 16, 16, 30, 16, 16, 16),
    "G": (14, 17, 16, 19, 17, 17, 14),
    "H": (17, 17, 17, 31, 17, 17, 17),
    "I": (14, 4, 4, 4, 4, 4, 14),
    "J": (1, 1, 1, 1, 17, 17, 14),
    "K": (17, 18, 20, 24, 20, 18, 17),
    "L": (16, 16, 16, 16, 16, 16, 31),
    "M": (17, 27, 21, 21, 17, 17, 17),
    "N": (17, 25, 21, 19, 17, 17, 17),
    "O": (14, 17, 17, 17, 17, 17, 14),
    "P": (30, 17, 17, 30, 16, 16, 16),
    "Q": (14, 17, 17, 17, 21, 18, 13),
    "R": (30, 17, 17, 30, 20, 18, 17),
    "S": (14, 17, 16, 14, 1, 17, 14),
    "T": (31, 4, 4, 4, 4, 4, 4),
    "U": (17, 17, 17, 17, 17, 17, 14),
    "V": (17, 17, 17, 17, 17, 10, 4),
    "W": (17, 17, 17, 21, 21, 21, 10),
    "X": (17, 17, 10, 4, 10, 17, 17),
    "Y": (17, 17, 10, 4, 4, 4, 4),
    "Z": (31, 1, 2, 4, 8, 16, 31),
    "[": (14, 8, 8, 8, 8, 8, 14),
    "\\": (16, 16, 8, 4, 2, 1, 1),
    "]": (14, 2, 2, 2, 2, 2, 14),
    "^": (4, 10, 17, 0, 0, 0, 0),
    "_": (0, 0, 0, 0, 0, 0, 31),
    "`": (8, 4, 2, 0, 0, 0, 0),
    "a": (0, 0, 14, 1, 15, 17, 15),
    "b": (16, 16, 30, 17, 17, 17, 30),
    "c": (0, 0, 14, 17, 16, 17, 14),
    "d": (1, 1, 15, 17, 17, 17, 15),
    "e": (0, 0, 14, 17, 31, 16, 14),
    "f": (6, 8, 8, 28, 8, 8, 8),
    "g": (0, 0, 15, 17, 15, 1, 14),
    "h": (16, 16, 30, 17, 17, 17, 17),
    "i": (4, 0, 12, 4, 4, 4, 14),
    "j": (2, 0, 6, 2, 2, 18, 12),
    "k": (16, 16, 18, 20, 24, 20, 18),
    "l": (12, 4, 4, 4, 4, 4, 14),
    "m": (0, 0, 26, 21, 21, 17, 17),
    "n": (0, 0, 30, 17, 17, 17, 17),
    "o": (0, 0, 14, 17, 17, 17, 14),
    "p": (0, 0, 30, 17, 30, 16, 16),
    "q": (0, 0, 15, 17, 15, 1, 1),
    "r": (0, 0, 22, 25, 16, 16, 16),
    "s": (0, 0, 15, 16, 14, 1, 30),
    "t": (8, 8, 28, 8, 8, 9, 6),
    "u": (0, 0, 17, 17, 17, 17, 15),
    "v": (0, 0, 17, 17, 17, 10, 4),
    "w": (0, 0, 17, 17, 21, 21, 10),
    "x": (0, 0, 17, 10, 4, 10, 17),
    "y": (0, 0, 17, 17, 15, 1, 14),
    "z": (0, 0, 31, 2, 4, 8, 31),
    "{": (2, 4, 4, 8, 4, 4, 2),
    "|": (4, 4, 4, 4, 4, 4, 4),
    "}": (8, 4, 4, 2, 4, 4, 8),
    "~": (0, 0, 8, 21, 2, 0, 0),
    "°": (4, 10, 4, 0, 0, 0, 0),
    "…": (0, 0, 0, 0, 0, 21, 0),
    "—": (0, 0, 0, 31, 0, 0, 0),
    "–": (0, 0, 0, 14, 0, 0, 0),
    "×": (0, 17, 10, 4, 10, 17, 0),
    "•": (0, 0, 4, 14, 4, 0, 0),
}

# precomputed pixel offsets per glyph at scale=1: list[(dx,dy)]
_PIX1: dict[str, list[tuple[int, int]]] = {}
_PIX2: dict[str, list[tuple[int, int]]] = {}


def _build_pixels(g: tuple[int, ...], scale: int) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for row in range(_H):
        bits = g[row]
        for col in range(_W):
            if bits & (1 << (_W - 1 - col)):
                if scale == 1:
                    out.append((col, row))
                else:
                    for dy in range(scale):
                        for dx in range(scale):
                            out.append((col * scale + dx, row * scale + dy))
    return out


def _ensure_cache() -> None:
    if _PIX1:
        return
    for ch, g in _GLYPHS.items():
        _PIX1[ch] = _build_pixels(g, 1)
        _PIX2[ch] = _build_pixels(g, 2)


def glyph(ch: str) -> tuple[int, ...]:
    if ch in _GLYPHS:
        return _GLYPHS[ch]
    if ch.isspace():
        return _GLYPHS[" "]
    low = ch.lower()
    if low in _GLYPHS:
        return _GLYPHS[low]
    return _GLYPHS.get("?", _GLYPHS[" "])


def text_width(text: str, scale: int = 1, tracking: int = 1) -> int:
    if not text:
        return 0
    return len(text) * (_W * scale + tracking) - tracking


def text_height(scale: int = 1) -> int:
    return _H * scale


def iter_pixels(text: str, scale: int = 1, tracking: int = 1):
    """Yield (x, y) pixel offsets — uses precomputed glyph caches."""
    _ensure_cache()
    cache = _PIX2 if scale == 2 else None
    x0 = 0
    step = _W * scale + tracking
    for ch in text:
        if scale == 1:
            pix = _PIX1.get(ch)
            if pix is None:
                if ch.isspace():
                    pix = _PIX1.get(" ")
                else:
                    pix = _PIX1.get(ch.lower()) or _PIX1.get("?", [])
            for dx, dy in pix:
                yield x0 + dx, dy
        elif scale == 2 and cache is not None:
            pix = cache.get(ch)
            if pix is None:
                if ch.isspace():
                    pix = cache.get(" ")
                else:
                    pix = cache.get(ch.lower()) or cache.get("?", [])
            for dx, dy in pix:
                yield x0 + dx, dy
        else:
            g = glyph(ch)
            for row in range(_H):
                bits = g[row]
                for col in range(_W):
                    if bits & (1 << (_W - 1 - col)):
                        basex = x0 + col * scale
                        basey = row * scale
                        for dy in range(scale):
                            for dx in range(scale):
                                yield basex + dx, basey + dy
        x0 += step


# warm cache at import (tiny)
_ensure_cache()
