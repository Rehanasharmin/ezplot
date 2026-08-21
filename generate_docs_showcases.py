#!/usr/bin/env python3
"""Regenerate the README gallery images in docs/.

Run from the repo root:

    python generate_docs_showcases.py
"""

from __future__ import annotations

import datetime as dt
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ezplot as ez

DOCS = ROOT / "docs"
DOCS.mkdir(parents=True, exist_ok=True)


def out(name: str) -> str:
    return str(DOCS / name)


def save(plot, name: str):
    plot.save(out(name))
    return plot


def generate_hero() -> None:
    x = list(range(1, 13))
    actual = [48, 54, 53, 61, 67, 70, 74, 82, 88, 92, 96, 104]
    target = [46, 50, 55, 58, 62, 67, 72, 76, 81, 87, 92, 98]
    p = (
        ez.line(x, [actual, target], labels=["Actual", "Target"])
        .t("Fast charts. Cleaner rendering.")
        .subtitle("Pure-Python PNG / SVG engine • sharp labels • production-ready defaults")
        .xlabel("Month")
        .ylabel("Index")
        .theme("dark")
        .colors("#60a5fa", "#f59e0b")
        .linewidth(3)
        .markers(False)
        .axhspan(72, 90, color="#22c55e", alpha=0.14)
        .vline(8, color="#94a3b8", dashed=True)
        .annotate(12, actual[-1], "render fix update", color="#f8fafc", anchor="end")
        .legend_pos("top-left")
        .footnote("ezplot README showcase")
        .size(960, 520)
    )
    save(p, "hero.png")


def generate_bar() -> None:
    p = (
        ez.bar({"Mon": 84, "Tue": 93, "Wed": 89, "Thu": 108, "Fri": 101, "Sat": 76})
        .t("Weekly signups")
        .ylabel("users")
        .palette("ocean")
        .values("{:.0f}")
        .legend(False)
        .axhspan(90, 110, color="#22c55e", alpha=0.08)
    )
    save(p, "bar.png")


def generate_stacked() -> None:
    p = (
        ez.bar(
            ["Q1", "Q2", "Q3", "Q4"],
            [[18, 22, 24, 28], [12, 15, 17, 19], [5, 7, 8, 9]],
            labels=["Platform", "Services", "Ops"],
        )
        .stacked()
        .t("Quarterly mix")
        .ylabel("$M")
        .theme("minimal")
        .legend_pos("top-left")
    )
    save(p, "stacked.png")


def generate_scatter() -> None:
    random.seed(14)
    xs = [random.uniform(0, 10) for _ in range(70)]
    ys = [1.1 * x + random.gauss(0, 1.0) + 1.5 for x in xs]
    p = (
        ez.scatter(xs, ys)
        .t("Acquisition efficiency")
        .xlabel("Spend")
        .ylabel("Signups")
        .color("#e11d48")
        .point_size(5.5)
        .alpha(0.7)
        .hline(8, color="#94a3b8")
        .vline(6, color="#94a3b8")
    )
    save(p, "scatter.png")


def generate_donut() -> None:
    p = (
        ez.donut({"Product": 41, "Growth": 24, "Infra": 18, "Ops": 17})
        .t("Team allocation")
        .theme("paper")
    )
    save(p, "donut.png")


def generate_hist() -> None:
    random.seed(21)
    samples = [random.gauss(72, 8) for _ in range(900)]
    p = ez.hist(samples, 22, t="Latency distribution", palette="sunset")
    save(p, "hist.png")


def generate_area() -> None:
    x = list(range(30))
    y = [18 + 5 * math.sin(i / 4) + 0.45 * i for i in x]
    p = (
        ez.area(x, y)
        .t("Traffic momentum")
        .xlabel("Day")
        .ylabel("k visits")
        .theme("dark")
        .color("#22c55e")
        .axhspan(24, 28, color="#60a5fa", alpha=0.08)
    )
    save(p, "area.png")


def generate_hbar() -> None:
    p = (
        ez.barh(
            ["Python", "TypeScript", "Go", "Rust", "Ruby"],
            [98, 89, 76, 72, 46],
            values="{:.0f}",
        )
        .t("Developer preference")
        .palette("sunset")
    )
    save(p, "hbar.png")


def generate_theme_cards() -> None:
    x = list(range(1, 9))
    y = [28, 34, 31, 40, 46, 43, 51, 57]
    common = dict(title="Theme preview", xlabel="Sprint", ylabel="Score")
    save(ez.line(x, y, c="#3b82f6", **common).theme("light"), "theme_light.png")
    save(ez.line(x, y, c="#60a5fa", **common).theme("dark"), "theme_dark.png")
    save(ez.line(x, y, c="#10b981", **common).theme("minimal"), "theme_minimal.png")
    save(ez.line(x, y, c="#c2410c", **common).theme("paper"), "theme_paper.png")


def generate_showcase_datetime() -> None:
    dates = [dt.datetime(2026, 1, d) for d in range(1, 11)]
    values = [12, 15, 14, 18, 22, 20, 24, 25, 23, 28]
    p = (
        ez.line(dates, values)
        .t("Smart Datetime Axis")
        .xlabel("Date")
        .ylabel("Requests")
        .color("#2563eb")
        .axhspan(19, 24, color="#22c55e", alpha=0.10)
    )
    save(p, "showcase_datetime.png")


def generate_showcase_custom() -> None:
    def draw_target_zone(r):
        r.draw_line(r.x0, 230, r.x1, 230, "#ef4444", width=1.5, dashed=True)
        r.draw_text(r.x0 + (r.x1 - r.x0) * 0.02, 238, "Target Threshold", "#ef4444", size=11)
        r.draw_rect(12, 72, 170, 34, "rgba(15,23,42,0.75)", raw_coords=True, radius=8)
        r.draw_text(24, 92, "custom primitives on top", "#f8fafc", raw_coords=True)

    x = [1, 2, 5, 6, 7, 8, 10]
    y = [150, 210, 210, 300, 360, 240, 320]
    p = (
        ez.line(x, y)
        .t("Custom Overlay Highlight (.draw())")
        .ylabel("Throughput")
        .axhspan(180, 280, color="#10b981", alpha=0.15)
        .draw(draw_target_zone)
    )
    save(p, "showcase_custom.png")


def generate_heatmap() -> None:
    random.seed(11)
    matrix = [[random.uniform(0, 100) for _ in range(8)] for _ in range(6)]
    p = ez.heatmap(
        matrix,
        row_labels=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
        col_labels=[f"h{i}" for i in range(8)],
        cmap="viridis",
        t="Load by hour",
    )
    save(p, "heatmap.png")


def generate_boxplot() -> None:
    random.seed(5)
    data = {
        "A": [random.gauss(10, 2) for _ in range(60)],
        "B": [random.gauss(14, 3) for _ in range(60)],
        "C": [random.gauss(12, 4) for _ in range(60)],
        "D": [random.gauss(16, 2) for _ in range(60)] + [30, 32],
    }
    save(ez.boxplot(data, t="Distribution spread"), "boxplot.png")


def generate_step() -> None:
    save(
        ez.step([0, 1, 2, 3, 4, 5, 6], [0, 2, 1, 3, 4, 2, 3], t="Step chart"),
        "step.png",
    )


def generate_log() -> None:
    x = list(range(1, 9))
    y = [2 ** i for i in range(8)]
    p = ez.line(x, y, t="Log scale", logy=True, c="#8b5cf6")
    save(p, "log.png")


def generate_trend() -> None:
    random.seed(9)
    xs = [random.uniform(0, 10) for _ in range(40)]
    ys = [0.9 * v + random.gauss(0, 1.3) + 1 for v in xs]
    p = ez.scatter(xs, ys, t="Trend line", c="#0ea5e9").trend(color="#f97316")
    save(p, "trend.png")


def generate_function() -> None:
    p = ez.fn(lambda x: math.sin(x) * 10 + 20, 0, 12, t="ez.fn(lambda x: …)", c="#7c3aed")
    save(p, "fn.png")


def generate_errors() -> None:
    p = (
        ez.line([1, 2, 3, 4, 5], [3, 5, 4, 7, 6], t="Error bars", c="#2563eb")
        .yerr([0.4, 0.2, 0.5, 0.3, 0.6])
        .markers(True)
    )
    save(p, "errors.png")


def main() -> None:
    ez.reset_defaults()
    ez.defaults(width=720, height=420, dpi=2)

    generate_hero()
    generate_bar()
    generate_stacked()
    generate_scatter()
    generate_donut()
    generate_hist()
    generate_area()
    generate_hbar()
    generate_theme_cards()
    generate_showcase_datetime()
    generate_showcase_custom()
    generate_heatmap()
    generate_boxplot()
    generate_step()
    generate_log()
    generate_trend()
    generate_function()
    generate_errors()

    print("README showcase images regenerated:")
    for path in sorted(DOCS.glob("*.png")):
        print(f"  {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
