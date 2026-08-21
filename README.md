# ezplot

**Dead-simple, fast plotting for Python.**

One-liners · PNG / JPEG / SVG · zero *required* dependencies · production knobs.

<p align="center">
  <img src="docs/hero.png" alt="ezplot hero chart" width="720"/>
</p>

```python
import ezplot as ez

ez.line([1, 3, 2, 5], t="Growth", save="growth.png")
ez.bar({"A": 10, "B": 25}, t="Sales", save="sales.jpg")
```

---

## New Release Showcase (v1.6.0)

`ezplot` now ships **7 new chart types**, **working log scales**, **trend lines, smoothing & error bars**, and an even smarter one-liner syntax:

```python
ez.heatmap(matrix, row_labels=days, col_labels=hours, save="heat.png")   # heatmap + colorbar
ez.boxplot({"A": a, "B": b, "C": c}, t="Boxes", save="box.png")          # Tukey whiskers + outliers
ez.step(x, y, t="Steps", save="s.png")                                   # step chart
ez.fn(lambda x: x**2, -5, 5, t="x²", save="f.png")                       # plot any callable

ez.line(x, y, logy=True, save="log.png")                # real log axes (ticks at decades)
ez.scatter(x, y).trend().yerr(errs).save("fit.png")     # regression line + error bars
ez.line(x, y1, y2, y3)                                  # multi-series, index detected
```

| Heatmap | Boxplot | Step | Log scale |
|:--:|:--:|:--:|:--:|
| <img src="docs/heatmap.png" alt="heatmap" width="180"/> | <img src="docs/boxplot.png" alt="boxplot" width="180"/> | <img src="docs/step.png" alt="step" width="180"/> | <img src="docs/log.png" alt="log" width="180"/> |
| Trend line | Function plot | Error bars | Datetime Axis |
| <img src="docs/trend.png" alt="trend" width="180"/> | <img src="docs/fn.png" alt="fn" width="180"/> | <img src="docs/errors.png" alt="errors" width="180"/> | <img src="docs/showcase_datetime.png" alt="datetime axis" width="180"/> |

Still here from 1.5.0: the **Datetime Axis** and **Infinite Customizability** via post-render primitive overlays / custom series rendering:

| Smart Datetime Axis | Infinite Custom Drawing Overlays |
|:--:|:--:|
| <img src="docs/showcase_datetime.png" alt="datetime axis" width="360"/> | <img src="docs/showcase_custom.png" alt="custom overlays" width="360"/> |
| *Auto-scaled dates, auto-formatted & auto-rotated labels* | *Drawn target regions, custom dashed thresholds, text layers* |

---

## Install

```bash
# from GitHub
pip install "git+https://github.com/Rehanasharmin/ezplot.git"

# or clone / local
git clone https://github.com/Rehanasharmin/ezplot.git
cd ezplot
pip install -e .

# optional — only for JPEG / WebP (PNG is built-in)
pip install pillow
# or:
pip install -e ".[images]"
```

**Python 3.8+** · MIT license

---

## Gallery

| | |
|:--:|:--:|
| <img src="docs/bar.png" alt="bar" width="360"/> | <img src="docs/stacked.png" alt="stacked" width="360"/> |
| *Bar + value labels* | *Stacked multi-series* |
| <img src="docs/scatter.png" alt="scatter" width="360"/> | <img src="docs/donut.png" alt="donut" width="360"/> |
| *Scatter + ref lines* | *Donut (paper theme)* |
| <img src="docs/hist.png" alt="hist" width="360"/> | <img src="docs/area.png" alt="area" width="360"/> |
| *Histogram* | *Area (dark)* |
| <img src="docs/hbar.png" alt="hbar" width="360"/> | <img src="docs/theme_dark.png" alt="dark" width="360"/> |
| *Horizontal bars* | *Dark theme* |

---

## Super short API

```python
import ezplot as ez

# style + save in one call
ez.line([1, 3, 2, 5], t="Hi", c="coral", save="hi.png")
ez.bar({"Mon": 12, "Tue": 19}, t="Visitors", save="v.jpg")
ez.pie({"A": 40, "B": 60}, donut=True, save="pie.png")
ez.hist(samples, 20, t="Dist", save="hist.png")
ez.auto(data, save="chart.png")          # picks chart type (incl. heatmap!)
ez.quick([1, 2, 3, 5])                   # auto + show

# 1.6 chart types
ez.step(x, y, save="step.png")
ez.boxplot(data, labels=["A", "B"], save="box.png")
ez.heatmap(matrix, row_labels=rows, col_labels=cols, save="heat.png")
ez.function(lambda x: x**2, -5, 5, save="f.png")
ez.barh(cats, vals, values=True)         # horizontal bars
ez.donut({"A": 40, "B": 60})             # donut shortcut
ez.chart(anything)                       # alias for ez.auto

# fluent
(
    ez.line(x, [y1, y2], labels=["A", "B"])
    .t("Revenue")
    .subtitle("FY2026")
    .xlabel("Month").ylabel("USD")
    .theme("dark")
    .axhspan(80, 120, color="#22c55e", alpha=0.15)  # target zone (background)
    .hline(100, color="#fbbf24")                    # target line
    .annotate(6, y1[6], "launch")
    .trend(color="#f43f5e", label="projection")     # linear regression overlay
    .yerr(5)                                        # error bars (scalar or list)
    .smooth(3)                                      # centered moving average
    .xrot(45)                                       # rotate x tick labels
    .legend_pos("top-left")
    .footnote("Source: finance")
    .dpi(2)                                         # retina PNG
    .png("out.png")
)
```

### Datetime Axis Intelligence

`ezplot` automatically understands Python `datetime.datetime` and `datetime.date` objects. It coerces them to Unix timestamps, computes nice tick intervals automatically based on the axis span (from years down to seconds), and formats and auto-rotates crowded labels dynamically!

```python
import datetime
import ezplot as ez

dates = [datetime.datetime(2026, 1, i) for i in range(1, 11)]
values = [12, 15, 14, 18, 22, 20, 24, 25, 23, 28]

ez.line(dates, values, t="Smart Datetime Axis", save="dates.png")
```

### Infinite Customizability (Create ANY Chart)

With `ezplot 1.5.0`, you are no longer limited to built-in chart types. You can create **any** chart you can imagine using our primitive drawing API or our post-render `.draw()` callback.

#### Unified Primitive Drawing API
Both `SVGRenderer` and `RasterRenderer` expose the same clean, fast drawing methods with full **color-parsing alpha/opacity** support:
- `to_pixels(x, y)`: Converts data coordinates to screen pixels.
- `draw_line(x1, y1, x2, y2, color, width=1.5, dashed=False, raw_coords=False, opacity=1.0)`
- `draw_rect(x, y, w, h, color, fill=True, stroke_color=None, stroke_width=1.0, radius=0.0, raw_coords=False, opacity=1.0)`
- `draw_circle(cx, cy, r, color, fill=True, stroke_color=None, stroke_width=1.0, raw_coords=False, opacity=1.0)`
- `draw_text(x, y, text, color, size=11, align="start", raw_coords=False, opacity=1.0)`
- `draw_polygon(pts, color, fill=True, stroke_color=None, stroke_width=1.0, raw_coords=False, opacity=1.0)`

#### 1. Post-Render Overlays (`.draw()`)
Easily overlay annotations, custom target lines, or extra graphics using a fluent chain:
```python
def draw_threshold_markers(r):
    # Draw custom annotations on the fly
    r.draw_line(r.x0, 230, r.x1, 230, "red", width=1.5, dashed=True)
    r.draw_text(r.x0 + (r.x1 - r.x0) * 0.02, 238, "Threshold", "red")

(
    ez.line(x, y)
    .t("Metrics")
    .draw(draw_threshold_markers)
    .save("metrics_threshold.png")
)
```

#### 2. High-level Background Spans (`.axhspan()` & `.axvspan()`)
Draw professional target bands or background highlight regions underneath your data series so your plot lines and markers are never obscured:
```python
(
    ez.line(x, y)
    .t("Metrics Highlight")
    .axhspan(180, 280, color="#10b981", alpha=0.15)  # Target safe zone
    .axvspan(1.5, 3.5, color="#3b82f6", alpha=0.10)  # Highlight phase
    .save("metrics_highlight.png")
)
```

#### 2. Custom Series (`kind="custom"`)
Build fully custom series types (like boxplots, candlestick charts, error bars, step charts) by providing a render function as the `color` attribute:
```python
def draw_error_bars(r):
    # Custom rendering logic using r.draw_line(), r.draw_circle() etc.
    for px, py in zip(x, y):
        r.draw_line(px, py - 2, px, py + 2, "red", width=2)
        r.draw_circle(px, py, 4, "blue")

p = ez.Plot(kind="custom")
p.add(x, y, color=draw_error_bars)
p.save("custom_chart.png")
```

### Shortcuts

| Short | Means |
|-------|--------|
| `t=` / `.t()` | title |
| `c=` / `.color()` | color |
| `w=` / `h=` | size |
| `lw=` | linewidth |
| `s=` | point size |
| `hbar=True` / `.horizontal()` | horizontal bars |
| `stacked=True` / `.stacked()` | stacked bars |
| `logy=True` / `.logy()`, `logx=` | log scale (decade ticks) |
| `trend=True` / `.trend()` | regression trend line |
| `yerr=` / `.yerr()`, `xerr=` | error bars |
| `smooth=` / `.smooth()` | moving-average smoothing |
| `step=True` / `.step()` | step rendering |
| `sort=True` / `.sort()` | bars sorted by value |
| `xrot=45` / `.xrot()` | rotate x tick labels |
| `values=True` / `.values()` | bar labels (`.values("{:.1f}")` for a format) |
| `save="f.png"` | write by extension |
| `.png()` / `.jpg()` | explicit helpers |

---

## Diagnostics: warnings, errors, and recovery details

`ezplot` is intentionally forgiving: it renders a visible fallback chart instead of crashing when practical. Every plot includes a structured diagnostic interpreter so applications can inspect recoveries, warnings, and rendering failures.

```python
p = ez.line([-2, 1, 4]).logy().style(colourr="coral")
p.svg()

for message in p.diagnostics():
    print(message.code, message.severity.value, message.message)
# ezplot.style.unknown_option warning Unknown style option(s) ignored
# ezplot.axis.logy_fallback warning Log y-axis disabled because data contains zero or negative values

print(p.diagnostic_report())       # formatted report for logs / support tickets
print(p.has_errors())              # True for error or critical messages
p.clear_diagnostics()
```

Each entry has a stable `code`, severity (`debug`, `info`, `warning`, `error`, or `critical`), UTC timestamp, context, and `to_dict()` for JSON logging. Factory/configuration events use the process-wide interpreter: `ez.diagnostics()`. To turn an integration exception into the same format, call `ez.interpret_exception(exc, phase="import")`.

## Customization (production-ready)

### Process-wide defaults

```python
ez.defaults(theme="dark", width=900, height=480, dpi=2, quality=92)
ez.line(y, t="Uses dark + retina automatically", save="a.png")

ez.reset_defaults()   # back to factory settings
```

### Per-plot controls

```python
(
    ez.bar(cats, vals)
    .t("Title").subtitle("Context line")
    .footnote("Source / notes")
    .theme("minimal").palette("ocean")
    .bg("#0b1220")                 # override background
    .legend_pos("bottom-right")    # tr | tl | br | bl
    .grid(False).tight()
    .margin(left=80, bottom=70)
    .xlim(0, 10).ylim(0, 100)
    .xticks([0, 5, 10]).yticks([0, 50, 100])
    .hline(50, color="orange", dashed=True)
    .vline(3, color="#94a3b8")
    .annotate(4, 80, "note", color="#ef4444")
    .values()                      # bar labels
    .stacked()                     # multi-series bars
    .dpi(2).save("report.png")
)
```

### Themes

| light | dark | minimal | paper |
|:--:|:--:|:--:|:--:|
| <img src="docs/theme_light.png" width="180" alt="light"/> | <img src="docs/theme_dark.png" width="180" alt="dark"/> | <img src="docs/theme_minimal.png" width="180" alt="minimal"/> | <img src="docs/theme_paper.png" width="180" alt="paper"/> |

```python
ez.set_theme("dark")   # global
ez.line(y, theme="paper", palette="sunset", save="x.png")
```

**Palettes:** `default` · `pastel` · `dark` · `mono` · `ocean` · `sunset` · `forest` · `candy` · `blues` · `reds`

**Heatmap colormaps:** `blues` · `greens` · `reds` · `oranges` · `purples` · `cool` · `warm` · `gray` · `viridis`

---

## Image formats

| Extension | Backend |
|-----------|---------|
| **`.png`** | **Built-in** (pure Python) |
| `.jpg` / `.jpeg` | Pillow |
| `.webp` | Pillow |
| `.svg` | Built-in vector |
| `.html` | Built-in page |

```python
p = ez.line([1, 2, 3, 5]).t("Demo")
p.save("a.png")           # PNG
p.save("a.jpg")           # JPEG
p.save("a.svg")           # SVG
p.png("a.png")
p.jpg("a.jpg", quality=85)
raw = p.png_bytes()       # for APIs / HTTP responses
img = p.image()           # PIL.Image (needs Pillow)
```

---

## Smart inputs

```python
ez.bar({"A": 10, "B": 20})           # dict → bar
ez.pie({"X": 40, "Y": 60})           # dict → pie
ez.scatter([(1, 2), (3, 1), (4, 5)]) # pairs
ez.line({"A": [1, 2], "B": [2, 1]})  # named series
ez.bar(["cat", "dog", "cat"])        # frequency count
ez.line([1, None, 4, 5])             # NaN gaps OK
ez.line(y1, y2, y3)                  # multi-series, shared index
ez.line(x, y1, y2)                   # index-like first arg → x axis
ez.bar(["A", "B"], s1, s2)           # positional grouped series
ez.line(df)                          # pandas DataFrame → named series
ez.auto(anything)                    # pick the chart (incl. 2D matrix → heatmap)

# datetimes work everywhere: data, ticks, limits, reference lines
ez.line(dates, values)
ez.line(dates, values).xlim(d1, d2).vline(launch_date).xticks([d1, d2])
```

---

## Why ezplot?

| | Matplotlib | **ezplot** |
|---|---|---|
| First plot | many lines | **1 line** |
| PNG | needs backend | **built-in** |
| Dependencies | heavy | **none** (Pillow optional) |
| Style | verbose | `t=`, `c=`, `save=` |
| Defaults | rcParams maze | `ez.defaults(...)` |

Typical PNG render: **~5–15 ms** for common charts (pure Python).

---

## Develop / test

```bash
git clone https://github.com/Rehanasharmin/ezplot.git
cd ezplot
pip install -e ".[dev,images]"
python -m pytest tests/          # or: python tests/test_basic.py tests/test_features.py
python examples/demo.py          # writes examples/out/*.png
python generate_docs_showcases.py  # regenerates docs/*.png gallery
```

## Project layout

```
ezplot/
├── ezplot/           # package
├── docs/             # README gallery images (relative paths)
├── examples/demo.py
├── tests/test_basic.py
├── pyproject.toml
├── LICENSE
└── README.md
```

## License

MIT
