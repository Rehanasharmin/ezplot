# Changelog

## 1.5.0

- New high-level background highlighting APIs: `.axhspan(ymin, ymax)` and `.axvspan(xmin, xmax)` to easily draw background target regions and shaded bands.
- Spans and background highlight layers are rendered underneath the plot lines (not on top) to keep data points and charts completely visible.
- Full opacity/alpha support on all primitive drawing APIs (`draw_line`, `draw_rect`, `draw_circle`, `draw_text`, `draw_polygon`) in both SVGRenderer and RasterRenderer.
- Multi-format CSS color-parsing intelligence: parses `#RRGGBBAA` hex alpha and `rgba(...)` formats seamlessly.
- Truly rotated y-axis labels on RasterRenderer (replaces the stacked-character vertical labels with a clean counter-clockwise rotation).
- Proportional font scaling: correctly connected `.font_scale` parameter dynamically scales all titles, subtitles, footnotes, legends, annotations, and tick labels.
- Symmetrical, unified, and aesthetic dashed grid lines on SVGRenderer for a modern Matplotlib-inspired feel.

## 1.4.0

- Infinite Customizability: unified primitive drawing API on SVGRenderer and RasterRenderer (`draw_line`, `draw_rect`, `draw_circle`, `draw_text`, `draw_polygon`, `to_pixels`).
- Custom Series (`kind="custom"`) to design completely new chart types.
- Post-render overlays using the fluent `.draw(fn)` API.
- Datetime Axis Intelligence: automatic date and datetime coercion to Unix timestamps with smart tick scaling/formatting and label auto-rotation.

## 1.3.0

- Production customization: `defaults()`, subtitle/footnote, hline/vline, annotate
- Stacked bars, legend positions, tight/margins, dpi retina export, bg override
- README gallery with relative `docs/*.png` paths (GitHub-ready)
- Faster pure-Python raster engine (bulk row writes, Bresenham, zlib level 1)
- PNG always zero-deps; JPEG/WebP via optional Pillow

## 1.2.x

- PNG / JPEG / WebP / SVG / HTML export
- One-liner `save=`, style shortcuts (`t=`, `c=`, …)
- Smart inputs: dicts, pairs, frequency bars, `auto()`

## 1.1.x

- Stability, NaN gaps, themes, horizontal bars

## 1.0.0

- Initial release: line, bar, scatter, hist, pie, area, SVG
