from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import config
from data_sources import DashboardData, HolidayItem, VpnUsage


def theme_colors() -> dict[str, int]:
    if config.THEME == "light":
        return {"bg": 255, "text": 0, "muted": 120, "divider": 160}
    return {"bg": 0, "text": 255, "muted": 140, "divider": 70}


def find_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    # (path, ttc_index) — wrong TTC index causes garbled glyphs / black bars on macOS.
    candidates: list[tuple[str, int]] = [
        (config.FONT_PATH, 0),
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
        ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 0),
        ("/System/Library/Fonts/STHeiti Light.ttc", 0),
        ("/System/Library/Fonts/PingFang.ttc", 3),
        ("/System/Library/Fonts/PingFang.ttc", 0),
    ]

    for path, index in candidates:
        if not path:
            continue
        font_path = Path(path)
        if not font_path.exists():
            continue
        try:
            return ImageFont.truetype(str(font_path), size=size, index=index)
        except OSError:
            try:
                return ImageFont.truetype(str(font_path), size=size)
            except OSError:
                continue

    return ImageFont.load_default()


def text_bottom(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    font,
    *,
    fill: int,
) -> int:
    draw.text((x, y), text, fill=fill, font=font)
    _left, _top, _right, bottom = draw.textbbox((x, y), text, font=font)
    return bottom


def draw_section_title(
    draw: ImageDraw.ImageDraw, x: int, y: int, title: str, font, *, fill: int
) -> int:
    bottom = text_bottom(draw, x, y, title, font, fill=fill)
    return bottom + 28


def draw_divider(
    draw: ImageDraw.ImageDraw,
    y: int,
    width: int,
    margin: int,
    *,
    fill: int,
    right_x: int | None = None,
) -> int:
    end_x = right_x if right_x is not None else width - margin
    draw.line((margin, y, end_x, y), fill=fill, width=2)
    return y + 36


def draw_holiday_item(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    item: HolidayItem,
    title_font,
    detail_font,
    *,
    fill: int,
) -> int:
    title = item.name
    if item.is_estimate:
        title += "（农历估算）"

    y = text_bottom(draw, x, y, f"{title}  还有 {item.days_until} 天", title_font, fill=fill) + 8

    detail = item.date_range
    if item.off_days > 1:
        detail += f"（休{item.off_days}天）"
    return text_bottom(draw, x, y, detail, detail_font, fill=fill) + 20


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    text: str,
    font,
    *,
    fill: int,
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    draw.text((cx - width // 2, cy - height // 2), text, fill=fill, font=font)


def draw_vpn_donut(
    draw: ImageDraw.ImageDraw,
    usage: VpnUsage,
    *,
    cx: int,
    cy: int,
    radius: int,
    thickness: int,
    colors: dict[str, int],
) -> None:
    text_color = colors["text"]
    muted_color = colors["muted"]
    ring_bg = colors["divider"]
    ring_used = colors["text"] if config.THEME == "dark" else 30

    bbox = (cx - radius, cy - radius, cx + radius, cy + radius)
    draw.ellipse(bbox, outline=ring_bg, width=thickness)

    if usage.used_percent > 0:
        sweep = max(usage.used_percent / 100 * 360, 2)
        draw.arc(bbox, start=270, end=270 + sweep, fill=ring_used, width=thickness)

    percent_font = find_font(52)
    detail_font = find_font(28)

    draw_centered_text(
        draw, cx, cy - 18, f"{usage.used_percent:.1f}%", percent_font, fill=text_color
    )
    draw_centered_text(
        draw,
        cx,
        cy + 30,
        f"{usage.used_gb:.1f} / {usage.limit_gb:.0f} GB",
        detail_font,
        fill=muted_color,
    )

    label_y = cy + radius + 36
    draw_centered_text(
        draw,
        cx,
        label_y,
        f"剩余 {usage.remaining_gb:.1f} GB",
        detail_font,
        fill=muted_color,
    )

    if usage.days_until_reset == 0:
        reset_text = "今日清零"
    else:
        reset_text = f"还有 {usage.days_until_reset} 天清零"
    draw_centered_text(draw, cx, label_y + 44, reset_text, detail_font, fill=muted_color)


def render_dashboard(data: DashboardData, output_path: Path) -> Path:
    width, height = config.WIDTH, config.HEIGHT
    colors = theme_colors()
    image = Image.new("L", (width, height), colors["bg"])
    draw = ImageDraw.Draw(image)
    text_color = colors["text"]
    muted_color = colors["muted"]
    divider_color = colors["divider"]

    title_font = find_font(64)
    subtitle_font = find_font(42)
    section_font = find_font(40)
    body_font = find_font(38)
    detail_font = find_font(32)
    weather_font = find_font(58)
    holiday_title_font = find_font(48)
    rain_alert_font = find_font(40)

    margin = 48
    divider_right = 580 if data.vpn_usage is not None else None
    y = 44

    date_line = data.now.strftime("%Y年%m月%d日") + f"  {data.weekday}"
    y = text_bottom(draw, margin, y, date_line, title_font, fill=text_color) + 16
    y = text_bottom(draw, margin, y, data.lunar_date, subtitle_font, fill=text_color) + 12

    if data.jieqi_today:
        jieqi_line = f"今日节气 · {data.jieqi_today}"
    else:
        jieqi_line = f"下一个节气 · {data.next_jieqi_name}（{data.next_jieqi_date}）"
    y = text_bottom(draw, margin, y, jieqi_line, body_font, fill=text_color) + 16
    y = draw_divider(
        draw, y + 10, width, margin, fill=divider_color, right_x=divider_right
    )

    y = text_bottom(draw, margin, y, config.CITY_NAME, weather_font, fill=text_color) + 8
    y = text_bottom(
        draw, margin, y, f"{data.temperature}  {data.weather_text}", weather_font, fill=text_color
    ) + 16
    y = text_bottom(
        draw,
        margin,
        y,
        f"体感 {data.feels_like}   湿度 {data.humidity}",
        body_font,
        fill=text_color,
    ) + 16

    rain_font = rain_alert_font if data.rain_alert else body_font
    y = text_bottom(draw, margin, y, data.rain_hint, rain_font, fill=text_color) + 16

    y = text_bottom(
        draw,
        margin,
        y,
        f"紫外线 {data.uv_level}   AQI {data.aqi} {data.aqi_category}",
        body_font,
        fill=text_color,
    ) + 16
    y = text_bottom(draw, margin, y, data.tomorrow_weather, body_font, fill=text_color) + 16
    y = draw_divider(
        draw, y + 8, width, margin, fill=divider_color, right_x=divider_right
    )

    y = draw_section_title(draw, margin, y, "节假日", section_font, fill=text_color)
    if data.holiday_items:
        for item in data.holiday_items:
            y = draw_holiday_item(
                draw,
                margin + 8,
                y,
                item,
                holiday_title_font,
                detail_font,
                fill=text_color,
            )
    else:
        y = text_bottom(draw, margin + 8, y, "未来120天暂无节假日", body_font, fill=text_color) + 16

    if data.makeup_workdays:
        y += 10
        y = text_bottom(draw, margin + 8, y, "调休提醒", detail_font, fill=text_color) + 10
        for line in data.makeup_workdays:
            y = text_bottom(draw, margin + 8, y, f"· {line}", detail_font, fill=text_color) + 10

    if data.vpn_usage is not None:
        draw_vpn_donut(
            draw,
            data.vpn_usage,
            cx=width - 220,
            cy=820,
            radius=150,
            thickness=24,
            colors=colors,
        )

    updated = data.now.strftime("更新于 %m月%d日 %H:%M")
    draw.text((margin, height - 72), updated, fill=muted_color, font=detail_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG", optimize=True)
    return output_path
