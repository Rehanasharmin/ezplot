import datetime
import ezplot as ez

def generate_showcase_datetime():
    dates = [datetime.datetime(2026, 1, i) for i in range(1, 11)]
    values = [12, 15, 14, 18, 22, 20, 24, 25, 23, 28]
    ez.line(dates, values, t="Smart Datetime Axis", save="docs/showcase_datetime.png")

def generate_showcase_custom():
    def draw_target_zone(r):
        # Draw green band from y=180 to y=280
        r.draw_rect(0, 180, 11, 100, "#10b981", fill=True)
        # Draw red dashed line at y=230
        r.draw_line(0, 230, 11, 230, "red", width=1.5, dashed=True)
        # Draw text "Target Threshold" in red
        r.draw_text(0.6, 238, "Target Threshold", "red", size=11)

    x = [1, 2, 5, 6, 7, 8, 10]
    y = [150, 210, 210, 300, 360, 240, 320]

    p = ez.line(x, y).t("Custom Overlay Highlight (.draw())").draw(draw_target_zone)
    p.save("docs/showcase_custom.png")

if __name__ == "__main__":
    generate_showcase_datetime()
    generate_showcase_custom()
    print("Showcase images successfully generated and saved to docs/!")
