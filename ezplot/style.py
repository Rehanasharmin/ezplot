"""Themes, color palettes, and visual defaults for ezplot."""

from __future__ import annotations

# Curated palettes — vibrant, colorblind-friendly where possible
COLORS = {
    "default": [
        "#3b82f6",
        "#ef4444",
        "#22c55e",
        "#f59e0b",
        "#a855f7",
        "#06b6d4",
        "#f97316",
        "#ec4899",
    ],
    "pastel": [
        "#93c5fd",
        "#fca5a5",
        "#86efac",
        "#fcd34d",
        "#d8b4fe",
        "#67e8f9",
        "#fdba74",
        "#f9a8d4",
    ],
    "dark": [
        "#60a5fa",
        "#f87171",
        "#4ade80",
        "#fbbf24",
        "#c084fc",
        "#22d3ee",
        "#fb923c",
        "#f472b6",
    ],
    "mono": [
        "#1e293b",
        "#475569",
        "#64748b",
        "#94a3b8",
        "#cbd5e1",
        "#e2e8f0",
    ],
    "ocean": [
        "#0ea5e9",
        "#06b6d4",
        "#14b8a6",
        "#2dd4bf",
        "#67e8f9",
        "#a5f3fc",
    ],
    "sunset": [
        "#f43f5e",
        "#f97316",
        "#eab308",
        "#fb7185",
        "#fdba74",
        "#fde047",
    ],
}

THEMES = {
    "light": {
        "bg": "#ffffff",
        "fg": "#1e293b",
        "grid": "#e2e8f0",
        "axis": "#94a3b8",
        "title": "#0f172a",
        "muted": "#64748b",
        "font": "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
        "palette": "default",
    },
    "dark": {
        "bg": "#0f172a",
        "fg": "#e2e8f0",
        "grid": "#1e293b",
        "axis": "#475569",
        "title": "#f8fafc",
        "muted": "#94a3b8",
        "font": "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
        "palette": "dark",
    },
    "minimal": {
        "bg": "#fafafa",
        "fg": "#333333",
        "grid": "#eeeeee",
        "axis": "#cccccc",
        "title": "#111111",
        "muted": "#888888",
        "font": "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
        "palette": "mono",
    },
    "paper": {
        "bg": "#fffef7",
        "fg": "#2c2c2c",
        "grid": "#e8e4d9",
        "axis": "#b0a890",
        "title": "#1a1a1a",
        "muted": "#6b6560",
        "font": "Georgia, 'Times New Roman', serif",
        "palette": "sunset",
    },
}

_active_theme: str = "light"
_THEME_CACHE: dict[str, dict] = {k: dict(v) for k, v in THEMES.items()}
_PALETTE_CACHE: dict[str, list[str]] = {k: list(v) for k, v in COLORS.items()}


def themes() -> list[str]:
    """Return available theme names."""
    return list(THEMES.keys())


def set_theme(name: str) -> None:
    """Set the global theme used by new plots: light, dark, minimal, paper."""
    global _active_theme
    if name not in THEMES:
        raise ValueError(f"Unknown theme '{name}'. Choose from: {', '.join(THEMES)}")
    _active_theme = name


def get_theme(name: str | None = None) -> dict:
    """Return a theme dict (defaults to active theme)."""
    key = name or _active_theme
    return _THEME_CACHE.get(key) or _THEME_CACHE["light"]


def get_palette(name: str | None = None) -> list[str]:
    """Return a color palette list."""
    if name is None:
        name = get_theme()["palette"]
    return _PALETTE_CACHE.get(name) or _PALETTE_CACHE["default"]


def resolve_color(color: str | None, index: int = 0, palette: str | None = None) -> str:
    """Resolve a color string or fall back to palette by index."""
    if color:
        return color
    pal = get_palette(palette)
    return pal[index % len(pal)]
