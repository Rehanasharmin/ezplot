# Changelog

## Hotfix

**Performance / memory**

- Line rendering (PNG + SVG) is now streaming: points are scaled, drawn and discarded one at a time instead of being buffered into parallel scaled-tuple lists (`segs` / `stepped` / `all_pts`). Peak render overhead dropped from ~200 B/point to ~55 B/point; a 1M-point line chart now peaks at ~143 MB RSS (was ~281 MB) — on par with matplotlib — and multi-million-point series no longer risk an OOM kill on small machines.
- `_prepare_xy` computes axis extents with O(1) streaming aggregates instead of materialising full `all_x`/`all_y` copies of every series, and only copies series lists when they actually need transforming (sort/smooth/length-align).
- SVG step-mode paths are now built without O(n²) string concatenation.

**Alignment**

- Bars now meet the axis lines instead of floating above them: bar value ranges are anchored at zero (no padding past zero for one-sided data), and the axis line itself is drawn on the zero line whenever zero lies inside the range — for positive, negative and mixed-sign data, in both SVG and PNG.
- Categorical line/scatter charts no longer draw their points on a padded numeric scale while the tick labels sat on a separate 0..n scale — series and axis now share one mapping, so points/markers land exactly on the category tick marks (bar/box ticks stay at band centers).

**Performance / memory**

- PNG thick lines (width > 1.5 px) are drawn as a few parallel Bresenham strokes with round caps instead of stamping a filled circle per pixel — same visual thickness, ~4x faster end-to-end for a 5 000-point line PNG.
- SVG line/scatter and raster line/scatter point mapping is inlined for the common linear-axis case (no per-point method calls), and `to_float`/`is_datetime` fast-paths avoid `hasattr` probes for plain numbers — roughly 2x faster SVG line/scatter rendering.

**Fixes**

- **PNG heatmaps no longer show "Render error: can't multiply sequence by non-int of type 'float'"**: the colorbar outline passed float coordinates into the raster canvas' `hline`/`vline` fast paths, which required ints; the exception was swallowed and the error banner was baked over the chart (also dropping row/column labels). `hline`/`vline` now accept float coordinates.
- Heatmaps whose rows are all empty (e.g. `[[], []]`) now render a "No data" message instead of baking "Render error: division by zero" into the output.
- Raster (PNG) step charts no longer draw point markers on the synthetic step corners — markers now appear only on real data points, matching the SVG renderer.

## 1.6.0

**New chart types**

- `ez.heatmap(matrix, row_labels=…, col_labels=…, cmap=…)` — colored cell grid with optional value labels, row/column labels and a colorbar. 9 gradient colormaps. `ez.auto` detects 2D numeric matrices automatically.
- `ez.boxplot(data, labels=…)` — Tukey boxplots (1.5·IQR whiskers, median line, outlier dots) from a list, list-of-lists or dict. Supports `.horizontal()`.
- `ez.step(x, y)` — step chart (value holds until the next x), also available as `.step()` on line/area plots.
- `ez.function(fn, start, end)` / `ez.fn(fn, …)` — plot any Python callable over an interval.
- `ez.barh(...)` — horizontal bars shortcut. `ez.donut(...)` — donut shortcut. `ez.chart(...)` — alias for `ez.auto`.

**Analytics & analysis overlays**

- `.trend()` / `.trendline()` — least-squares linear regression line over line/scatter charts (auto legend entry).
- `.smooth(window)` — centered moving-average smoothing for line/area series.
- `.yerr(err)` / `.xerr(err)` — error bars with caps; scalar, per-point list, or per-series nested list.
- `.xrot(degrees)` / `.rotate_xticks()` — manual x tick label rotation (SVG honors any angle; raster uses vertical labels).

**Real log scales**

- `logy=True` / `.logy()` and `logx=True` / `.logx()` now actually render logarithmic axes with decade ticks (1, 10, 100, …) in both SVG and raster output. Non-positive data safely falls back to a linear axis.

**Smarter syntax (backward compatible)**

- `ez.line(y1, y2, y3)` treats all arguments as parallel series sharing an index; a first argument that looks like an index (0, 1, 2, …) is used as x. Same for `ez.scatter` and `ez.plot`.
- `ez.bar(cats, s1, s2)` — positional grouped series.
- `ez.bar({"A": 1, "B": 2}, values=True)` — the `values` label toggle now works as a factory keyword.
- Datetimes are accepted in `.xlim/.ylim/.xticks/.yticks/.hline/.vline/.annotate/.axhspan/.axvspan`.
- pandas-like DataFrames are split into named series using their column names.
- Unknown style keywords emit a `UserWarning` instead of being silently dropped.
- `.values(fmt)` accepts a format string (e.g. `.values("{:.1f}")`), also for horizontal bars.

**Bug fixes**

- Fixed `.logy()/.logx()` being silently ignored.
- Fixed stacked bars being drawn with a different y-range than the axes.
- Fixed horizontal bars showing meaningless 0–1 numeric labels on the category axis; value labels and reference lines now map correctly in horizontal mode.
- Fixed dashed lines rendering solid in raster (PNG/JPEG/WebP) output.
- Fixed `ez.line(y1, y2, y3)` silently using the first series as x.
- Fixed `ez.bar(None, [1, 2, 3])` dropping all data.
- Fixed `.colors()` being ignored on single-series bar charts.
- Fixed `.xlim()/.annotate()/.hline()/…` rejecting datetime objects.
- Fixed area fills connecting across NaN gaps.
- Fixed annotate label offset for `anchor="end"` and added `size=` control.
- Fixed heatmap column labels not centering in raster output.
- Reference-line `width` is now honored in raster output.

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
