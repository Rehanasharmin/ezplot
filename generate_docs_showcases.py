import datetime
import math
import random

import ezplot as ez


def generate_showcase_datetime():
    dates = [datetime.datetime(2026, 1, i) for i in range(1, 11)]
    values = [12, 15, 14, 18, 22, 20, 24, 25, 23, 28]
    ez.line(dates, values, t="Smart Datetime Axis", save="docs/showcase_datetime.png")


def generate_showcase_custom():
    def draw_target_zone(r):
        # Draw red dashed line within exact axis bounds (r.x0 to r.x1)
        r.draw_line(r.x0, 230, r.x1, 230, "red", width=1.5, dashed=True)
        # Draw text "Target Threshold" in red slightly offset from the left axis
        r.draw_text(r.x0 + (r.x1 - r.x0) * 0.02, 238, "Target Threshold", "red", size=11)

    x = [1, 2, 5, 6, 7, 8, 10]
    y = [150, 210, 210, 300, 360, 240, 320]

    p = (
        ez.line(x, y)
        .t("Custom Overlay Highlight (.draw())")
        .axhspan(180, 280, color="#10b981", alpha=0.15)
        .draw(draw_target_zone)
    )
    p.save("docs/showcase_custom.png")


# --------------------------------------------------------------------------- #
# v1.6.0 gallery
# --------------------------------------------------------------------------- #

def generate_gallery_heatmap():
    random.seed(11)
    m = [[random.uniform(0, 100) for _ in range(8)] for _ in range(6)]
    ez.heatmap(
        m,
        row_labels=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
        col_labels=[f"h{i}" for i in range(8)],
        cmap="viridis",
        t="Heatmap",
        save="docs/heatmap.png",
    )


def generate_gallery_boxplot():
    random.seed(5)
    data = {
        "A": [random.gauss(10, 2) for _ in range(60)],
        "B": [random.gauss(14, 3) for _ in range(60)],
        "C": [random.gauss(12, 4) for _ in range(60)],
        "D": [random.gauss(16, 2) for _ in range(60)] + [30, 32],
    }
    ez.boxplot(data, t="Boxplot + outliers", save="docs/boxplot.png")


def generate_gallery_step():
    ez.step([0, 1, 2, 3, 4, 5, 6], [0, 2, 1, 3, 4, 2, 3], t="Step chart",
            save="docs/step.png")


def generate_gallery_log():
    x = [i for i in range(1, 9)]
    y = [2 ** i for i in range(8)]
    ez.line(x, y, t="Log scale", logy=True, save="docs/log.png")


def generate_gallery_trend():
    random.seed(9)
    xs = [random.uniform(0, 10) for _ in range(40)]
    ys = [0.8 * v + random.gauss(0, 1.5) for v in xs]
    ez.scatter(xs, ys, t="Trend line", trend=True, save="docs/trend.png")


def generate_gallery_function():
    ez.fn(lambda x: math.sin(x) * 10 + 20, 0, 12, t="ez.fn(lambda x: …)",
          save="docs/fn.png")


def generate_gallery_errors():
    ez.line([1, 2, 3, 4, 5], [3, 5, 4, 7, 6], t="Error bars",
            yerr=[0.4, 0.2, 0.5, 0.3, 0.6], save="docs/errors.png")


if __name__ == "__main__":
    generate_showcase_datetime()
    generate_showcase_custom()
    generate_gallery_heatmap()
    generate_gallery_boxplot()
    generate_gallery_step()
    generate_gallery_log()
    generate_gallery_trend()
    generate_gallery_function()
    generate_gallery_errors()
    print("Showcase images successfully generated and saved to docs/!")
