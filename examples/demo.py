#!/usr/bin/env python3
"""
ezplot demo — regenerate sample charts into examples/out/

Run from the repo root (or any cwd):

    python examples/demo.py
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

# Allow running without install: repo_root/ezplot package
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ezplot as ez

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    print(f"ezplot {ez.__version__} — writing demos → {OUT.relative_to(ROOT) if OUT.is_relative_to(ROOT) else OUT}")
    random.seed(7)

    ez.line([1, 3, 2, 5, 4, 7, 6], t="Simple line", c="#3b82f6", save=str(OUT / "01_line.png"))

    x = list(range(12))
    y1 = [math.sin(i / 2) * 10 + 12 for i in x]
    y2 = [math.cos(i / 2) * 8 + 10 for i in x]
    (
        ez.line(x, [y1, y2], labels=["sin", "cos"])
        .t("Waves")
        .xlabel("step")
        .ylabel("amplitude")
        .theme("dark")
        .save(OUT / "02_multi_line_dark.png")
    )

    (
        ez.bar({"Mon": 42, "Tue": 55, "Wed": 38, "Thu": 70, "Fri": 61})
        .t("Weekly visitors")
        .ylabel("people")
        .palette("ocean")
        .values()
        .save(OUT / "03_bar.png")
    )

    (
        ez.bar(
            ["Q1", "Q2", "Q3", "Q4"],
            [[12, 18, 15, 22], [10, 14, 19, 20], [5, 7, 9, 11]],
            labels=["2024", "2025", "Other"],
        )
        .t("Quarterly revenue")
        .stacked()
        .theme("minimal")
        .save(OUT / "04_stacked_bar.png")
    )

    xs = [random.uniform(0, 10) for _ in range(60)]
    ys = [0.8 * v + random.gauss(0, 1.2) for v in xs]
    (
        ez.scatter(xs, ys)
        .t("Noisy trend")
        .color("#e11d48")
        .point_size(6)
        .alpha(0.75)
        .hline(5)
        .save(OUT / "05_scatter.png")
    )

    data = [random.gauss(50, 12) for _ in range(800)]
    ez.hist(data, 24, t="Heights", palette="sunset", save=str(OUT / "06_hist.png"))

    (
        ez.pie({"Product": 35, "Services": 25, "Ads": 20, "Other": 12, "R&D": 8})
        .t("Budget split")
        .save(OUT / "07_pie.png")
    )

    (
        ez.pie({"Done": 40, "Doing": 30, "Todo": 30})
        .donut()
        .t("Sprint status")
        .theme("paper")
        .save(OUT / "08_donut_paper.png")
    )

    t = list(range(40))
    signal = [max(0, 10 + 5 * math.sin(i / 3) + random.uniform(-1, 1)) for i in t]
    (
        ez.area(t, signal)
        .t("Signal energy")
        .palette("ocean")
        .theme("dark")
        .save(OUT / "09_area_dark.png")
    )

    (
        ez.bar({"Python": 95, "JS": 88, "Go": 70, "Rust": 62, "Ruby": 40})
        .horizontal()
        .t("Language love")
        .palette("sunset")
        .save(OUT / "10_hbar.png")
    )

    (
        ez.line([1, 3, None, 5, 4, 8])
        .t("NaN gaps")
        .color("#a855f7")
        .save(OUT / "11_nan_gaps.png")
    )

    ez.auto({"North": 12, "South": 19, "East": 8, "West": 15}, t="ez.auto(dict)", save=str(OUT / "12_auto.png"))

    # SVG + HTML samples
    ez.line([1, 2, 3, 4, 5], [2, 5, 3, 8, 7], t="SVG export", save=str(OUT / "13_export.svg"))
    ez.bar([3, 1, 4], t="HTML export", save=str(OUT / "14_export.html"))

    # ---- 1.6 new features -------------------------------------------------

    (
        ez.heatmap(
            [[random.uniform(0, 1) for _ in range(8)] for _ in range(6)],
            row_labels=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            col_labels=[f"h{i}" for i in range(8)],
        )
        .t("Hourly heat")
        .save(OUT / "15_heatmap.png")
    )

    ez.boxplot(
        {
            "A": [random.gauss(10, 2) for _ in range(60)],
            "B": [random.gauss(14, 3) for _ in range(60)],
            "C": [random.gauss(12, 4) for _ in range(60)],
        },
        t="Boxplot + outliers",
        save=str(OUT / "16_boxplot.png"),
    )

    (
        ez.step([0, 1, 2, 3, 4, 5], [0, 2, 1, 3, 4, 2])
        .t("Step chart")
        .save(OUT / "17_step.png")
    )

    (
        ez.line([1, 2, 3, 4, 5, 6, 7], [2, 4, 8, 16, 32, 64, 128])
        .logy()
        .t("Log scale")
        .save(OUT / "18_log.png")
    )

    (
        ez.scatter(xs, ys)
        .t("Trend + errors")
        .trend()
        .yerr(1.0)
        .save(OUT / "19_trend_errors.png")
    )

    ez.fn(lambda x: math.sin(x) * 10, 0, 12, t="ez.fn(sin)", save=str(OUT / "20_fn.png"))

    print("Done. Files:")
    for p in sorted(OUT.iterdir()):
        print(f"  {p.name:24} {p.stat().st_size:7d} bytes")


if __name__ == "__main__":
    main()
