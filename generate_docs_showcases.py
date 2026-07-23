import datetime
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

if __name__ == "__main__":
    generate_showcase_datetime()
    generate_showcase_custom()
    print("Showcase images successfully generated and saved to docs/!")
