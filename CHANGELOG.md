# Changelog

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
