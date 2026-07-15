"""
Global defaults — production knobs for the whole process.

    import ezplot as ez
    ez.defaults(theme="dark", width=800, height=450, dpi=2)
"""

from __future__ import annotations

from typing import Any

_DEFAULTS: dict[str, Any] = {
    "theme": None,          # None → style active theme
    "width": 720,
    "height": 420,
    "dpi": 1,               # integer scale factor for raster export (2 = retina)
    "quality": 90,          # jpeg/webp
    "grid": True,
    "legend": True,
    "markers": None,        # None = auto
    "linewidth": 2.5,
    "point_size": 5.0,
    "alpha": 0.85,
    "palette": None,
    "font_scale": 1,
    "tight": False,
    "legend_pos": "top-right",  # top-right | top-left | bottom-right | bottom-left
    "bg": None,             # override theme background
}


def defaults(**kwargs: Any) -> dict[str, Any]:
    """
    Update and/or return global defaults.

        ez.defaults(theme="dark", width=900, dpi=2)
        cfg = ez.defaults()   # read current
    """
    if kwargs:
        for k, v in kwargs.items():
            if k in _DEFAULTS:
                _DEFAULTS[k] = v
            elif k == "size" and isinstance(v, (list, tuple)) and len(v) == 2:
                _DEFAULTS["width"], _DEFAULTS["height"] = int(v[0]), int(v[1])
            elif k in ("w",):
                _DEFAULTS["width"] = int(v)
            elif k in ("h",):
                _DEFAULTS["height"] = int(v)
    return dict(_DEFAULTS)


def get_defaults() -> dict[str, Any]:
    return dict(_DEFAULTS)


def reset_defaults() -> None:
    defaults(
        theme=None,
        width=720,
        height=420,
        dpi=1,
        quality=90,
        grid=True,
        legend=True,
        markers=None,
        linewidth=2.5,
        point_size=5.0,
        alpha=0.85,
        palette=None,
        font_scale=1,
        tight=False,
        legend_pos="top-right",
        bg=None,
    )
