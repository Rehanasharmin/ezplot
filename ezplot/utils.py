"""Small helpers: number formatting, data coercion, nice scales, smart inference."""

from __future__ import annotations

import math
import re
from typing import Any, Sequence


# ---------------------------------------------------------------------------
# data coercion
# ---------------------------------------------------------------------------

def as_list(data: Any) -> list:
    """Coerce array-like data to a plain Python list (numpy/pandas friendly)."""
    if data is None:
        return []
    if isinstance(data, (str, bytes)):
        return [data]
    if isinstance(data, dict):
        return list(data.values())
    if isinstance(data, (list, tuple)):
        return list(data)
    # pandas Series / Index / numpy ndarray
    if hasattr(data, "tolist"):
        try:
            return data.tolist()
        except Exception:
            pass
    # pandas DataFrame → list of column lists (caller may special-case)
    if hasattr(data, "columns") and hasattr(data, "__getitem__"):
        try:
            return [data[c].tolist() for c in data.columns]
        except Exception:
            pass
    try:
        return list(data)
    except TypeError:
        return [data]


def is_number(v: Any) -> bool:
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)):
        return math.isfinite(float(v))
    if isinstance(v, str):
        try:
            float(v.replace(",", ""))
            return True
        except ValueError:
            return False
    try:
        return math.isfinite(float(v))
    except (TypeError, ValueError):
        return False


def to_float(v: Any) -> float | None:
    """Parse a value to float; return None if missing/invalid/non-finite."""
    if v is None:
        return None
    if isinstance(v, bool):
        return float(int(v))
    if isinstance(v, (int, float)):
        f = float(v)
        return f if math.isfinite(f) else None
    if isinstance(v, str):
        s = v.strip().replace(",", "")
        if s == "" or s.lower() in {"nan", "none", "null", "na", "-"}:
            return None
        try:
            f = float(s)
            return f if math.isfinite(f) else None
        except ValueError:
            return None
    try:
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def as_float_list(data: Any, *, fill: float | None = None) -> list[float]:
    """
    Coerce to list of finite floats.
    Invalid values become `fill` (default 0.0). Pass fill=None to drop them
    is not supported here — use finite_pairs for drop behaviour.
    """
    if fill is None:
        fill = 0.0
    out: list[float] = []
    for v in as_list(data):
        f = to_float(v)
        out.append(fill if f is None else f)
    return out


def as_float_list_keep_nan(data: Any) -> list[float]:
    """Coerce to floats; invalid → math.nan (so renderers can skip gaps)."""
    out: list[float] = []
    for v in as_list(data):
        f = to_float(v)
        out.append(math.nan if f is None else f)
    return out


def as_str_list(data: Any) -> list[str]:
    return [str(v) for v in as_list(data)]


def looks_numeric_sequence(data: Any) -> bool:
    """True if most elements parse as numbers."""
    items = as_list(data)
    if not items:
        return False
    # nested list → not a flat numeric series
    if isinstance(items[0], (list, tuple)):
        return False
    sample = items[: min(32, len(items))]
    ok = sum(1 for v in sample if is_number(v))
    return ok >= max(1, int(0.7 * len(sample)))


def is_list_of_lists(data: Any) -> bool:
    items = as_list(data)
    if not items:
        return False
    first = items[0]
    if isinstance(first, (list, tuple)):
        return True
    # numpy 2d
    if hasattr(data, "ndim") and getattr(data, "ndim", 1) >= 2:
        return True
    return False


def is_list_of_pairs(data: Any) -> bool:
    """Detect [(x,y), (x,y), ...] or [[x,y], ...]."""
    items = as_list(data)
    if len(items) < 1:
        return False
    sample = items[: min(8, len(items))]
    for row in sample:
        if not isinstance(row, (list, tuple)) or len(row) != 2:
            return False
        if not is_number(row[0]) or not is_number(row[1]):
            return False
    return True


def unpack_pairs(data: Any) -> tuple[list[float], list[float]]:
    xs, ys = [], []
    for row in as_list(data):
        if isinstance(row, (list, tuple)) and len(row) >= 2:
            x, y = to_float(row[0]), to_float(row[1])
            if x is not None and y is not None:
                xs.append(x)
                ys.append(y)
    return xs, ys


def dict_to_xy(data: dict) -> tuple[list[str], list[float]]:
    """dict keys → categories, values → numbers (nested values summed if needed)."""
    keys = [str(k) for k in data.keys()]
    vals: list[float] = []
    for v in data.values():
        if isinstance(v, (list, tuple)):
            vals.append(sum(to_float(x) or 0.0 for x in v))
        else:
            vals.append(to_float(v) or 0.0)
    return keys, vals


def align_xy(
    xs: Sequence[float],
    ys: Sequence[float],
    *,
    drop_nan: bool = True,
    sort_x: bool = False,
) -> tuple[list[float], list[float]]:
    """Align, optionally drop non-finite, optionally sort by x."""
    n = min(len(xs), len(ys))
    pairs = []
    for i in range(n):
        x, y = xs[i], ys[i]
        if drop_nan:
            if not (isinstance(x, (int, float)) and math.isfinite(float(x))):
                continue
            if not (isinstance(y, (int, float)) and math.isfinite(float(y))):
                continue
        pairs.append((float(x), float(y)))
    if sort_x:
        pairs.sort(key=lambda p: p[0])
    if not pairs:
        return [], []
    return [p[0] for p in pairs], [p[1] for p in pairs]


def pad_series(series: list[float], n: int, fill: float = 0.0) -> list[float]:
    if len(series) >= n:
        return series[:n]
    return series + [fill] * (n - len(series))


# ---------------------------------------------------------------------------
# scales / ticks
# ---------------------------------------------------------------------------

def nice_number(value: float, round_up: bool = False) -> float:
    """Round to a 'nice' number for axis ticks (1, 2, 5 × 10^n)."""
    if value == 0 or not math.isfinite(value):
        return 0.0
    exp = math.floor(math.log10(abs(value)))
    frac = abs(value) / (10**exp)
    if round_up:
        if frac <= 1:
            nice = 1
        elif frac <= 2:
            nice = 2
        elif frac <= 5:
            nice = 5
        else:
            nice = 10
    else:
        if frac < 1.5:
            nice = 1
        elif frac < 3:
            nice = 2
        elif frac < 7:
            nice = 5
        else:
            nice = 10
    return math.copysign(nice * (10**exp), value)


def nice_ticks(lo: float, hi: float, n: int = 5) -> list[float]:
    """Generate ~n nice tick values spanning [lo, hi]."""
    if not math.isfinite(lo) or not math.isfinite(hi):
        return [0.0, 1.0]
    if n < 2:
        n = 2
    if lo > hi:
        lo, hi = hi, lo
    if lo == hi:
        pad = abs(lo) * 0.1 if lo != 0 else 1.0
        lo, hi = lo - pad, hi + pad

    raw_step = (hi - lo) / max(n - 1, 1)
    step = nice_number(raw_step, round_up=True)
    if step == 0 or not math.isfinite(step):
        step = 1.0

    # snap start to multiple of step
    start = math.floor(lo / step) * step
    # fix float drift
    decimals = max(0, -int(math.floor(math.log10(abs(step)))) + 2) if step != 0 else 6
    decimals = min(decimals, 12)

    ticks: list[float] = []
    for i in range(n * 6 + 4):
        t = round(start + i * step, decimals)
        if t > hi + step * 0.05:
            break
        if t >= lo - step * 0.05:
            # avoid -0.0
            if abs(t) < step * 1e-9:
                t = 0.0
            ticks.append(t)
    if not ticks:
        ticks = [lo, hi]
    # de-dupe while preserving order
    seen = set()
    uniq = []
    for t in ticks:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq


def format_number(v: float) -> str:
    """Compact human-readable number for tick labels."""
    if not math.isfinite(v):
        return "—"
    av = abs(v)
    if av == 0:
        return "0"
    if av >= 1e12:
        return f"{v / 1e12:.1f}T".replace(".0T", "T")
    if av >= 1e9:
        return f"{v / 1e9:.1f}B".replace(".0B", "B")
    if av >= 1e6:
        return f"{v / 1e6:.1f}M".replace(".0M", "M")
    if av >= 1e4:
        return f"{v / 1e3:.1f}k".replace(".0k", "k")
    if av >= 1e3 and float(v).is_integer():
        return f"{v / 1e3:.1f}k".replace(".0k", "k") if av >= 10000 else str(int(round(v)))
    if float(v).is_integer() or av >= 100:
        return str(int(round(v)))
    if av >= 1:
        return f"{v:.2f}".rstrip("0").rstrip(".")
    if av >= 0.01:
        return f"{v:.3f}".rstrip("0").rstrip(".")
    return f"{v:.2e}"


def data_range(
    values: Sequence[float],
    pad: float = 0.05,
    *,
    include_zero: bool = False,
) -> tuple[float, float]:
    """Min/max of finite values with optional fractional padding."""
    finite = [float(v) for v in values if isinstance(v, (int, float)) and math.isfinite(float(v))]
    if not finite:
        return 0.0, 1.0
    lo = min(finite)
    hi = max(finite)
    if include_zero:
        lo = min(lo, 0.0)
        hi = max(hi, 0.0)
    if lo == hi:
        d = abs(lo) * 0.1 if lo != 0 else 1.0
        return lo - d, hi + d
    span = hi - lo
    return lo - span * pad, hi + span * pad


def auto_bins(data: Sequence[float], bins: int | None = None) -> int:
    """Choose bin count: explicit, else Freedman–Diaconis (fallback Sturges)."""
    n = len(data)
    if n == 0:
        return 1
    if bins is not None:
        return max(int(bins), 1)
    if n < 2:
        return 1
    # Sturges fallback
    sturges = max(int(math.ceil(math.log2(n) + 1)), 5)
    try:
        s = sorted(float(v) for v in data if math.isfinite(float(v)))
        if len(s) < 4:
            return sturges
        q1 = s[len(s) // 4]
        q3 = s[(3 * len(s)) // 4]
        iqr = q3 - q1
        if iqr <= 0:
            return sturges
        width = 2 * iqr / (len(s) ** (1 / 3))
        if width <= 0:
            return sturges
        span = s[-1] - s[0]
        fd = int(math.ceil(span / width))
        return max(5, min(fd, 80))
    except Exception:
        return sturges


def histogram_bins(
    data: Sequence[float], bins: int | None = None
) -> tuple[list[float], list[float], list[float]]:
    """
    Histogram: returns (bin_edges, bin_centers, counts).
    """
    finite = [float(v) for v in data if isinstance(v, (int, float)) and math.isfinite(float(v))]
    if not finite:
        return [], [], []
    n_bins = auto_bins(finite, bins)
    lo, hi = min(finite), max(finite)
    if lo == hi:
        return [lo - 0.5, lo + 0.5], [lo], [float(len(finite))]
    width = (hi - lo) / n_bins
    edges = [lo + i * width for i in range(n_bins + 1)]
    counts = [0.0] * n_bins
    for v in finite:
        idx = int((v - lo) / width)
        if idx >= n_bins:
            idx = n_bins - 1
        if idx < 0:
            idx = 0
        counts[idx] += 1.0
    centers = [lo + (i + 0.5) * width for i in range(n_bins)]
    return edges, centers, counts


def escape_xml(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def unique_id(prefix: str = "ez") -> str:
    """Cheap unique-ish id for SVG clipPaths when embedding many charts."""
    import time
    import random
    return f"{prefix}{int(time.time() * 1000) % 10_000_000:x}{random.randint(0, 0xFFFF):04x}"


def truncate_label(text: str, max_len: int = 14) -> str:
    s = str(text)
    if len(s) <= max_len:
        return s
    if max_len <= 1:
        return s[:max_len]
    return s[: max_len - 1] + "…"


def infer_chart_kind(data: Any, y: Any = None) -> str:
    """
    Guess a sensible chart type from the data shape.

        dict                  → bar
        list of pairs         → scatter
        categories + numbers  → bar
        two numeric series    → scatter if many unordered-ish else line
        one numeric series    → line
        many categories       → bar
    """
    if isinstance(data, dict):
        return "bar"
    if y is None:
        if is_list_of_pairs(data):
            return "scatter"
        if looks_numeric_sequence(data):
            return "line"
        # list of strings? useless alone
        return "line"
    # x, y given
    if not looks_numeric_sequence(data) and looks_numeric_sequence(y):
        return "bar"
    if looks_numeric_sequence(data) and looks_numeric_sequence(y):
        xs = as_float_list(data)
        if len(xs) >= 3:
            # if x is sorted-ish → line, else scatter
            diffs = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
            if diffs and all(d >= 0 for d in diffs):
                return "line"
            return "scatter"
        return "line"
    return "line"
