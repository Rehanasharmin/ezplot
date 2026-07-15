"""
ezplot — dead-simple, fast plotting for Python.

    import ezplot as ez

    ez.line([1, 3, 2, 5], t="Growth", save="growth.png")
    ez.bar({"A": 10, "B": 25}, t="Sales", save="sales.jpg")
    ez.defaults(theme="dark", dpi=2)   # process-wide defaults
"""

from .core import Plot
from .charts import line, bar, scatter, hist, pie, area, plot, auto, quick
from .style import themes, set_theme, COLORS
from .config import defaults, reset_defaults, get_defaults

__version__ = "1.3.0"
__all__ = [
    "Plot",
    "line",
    "bar",
    "scatter",
    "hist",
    "pie",
    "area",
    "plot",
    "auto",
    "quick",
    "themes",
    "set_theme",
    "COLORS",
    "defaults",
    "reset_defaults",
    "get_defaults",
    "__version__",
]
