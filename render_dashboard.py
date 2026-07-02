from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import config
from data_sources import DashboardData


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


def text_bottom(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, font, fill: int = 0) -> int:
    draw.text((x, y), text, fill=fill, font=font)
    _left, _top, _right, bottom = draw.textbbox((x, y), text, font=font)
    return bottom


def draw_section_title(draw: ImageDraw.ImageDraw, x: int, y: int, title: str, font) -> int:
    bottom = text_bottom(draw, x, y, title, font)
    return bottom + 18


def draw_divider(draw: ImageDraw.ImageDraw, y: int, width: int, margin: int = 56) -> int:
    draw.line((margin, y, width - margin, y), fill=180, width=2)
    return y + 28


def render_dashboard(data: DashboardData, output_path: Path) -> Path:
    width, height = config.WIDTH, config.HEIGHT
    image = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(image)

    title_font = find_font(52)
    subtitle_font = find_font(34)
    body_font = find_font(30)
    small_font = find_font(24)
    weather_font = find_font(48)

    margin = 56
    y = 48

    date_line = data.now.strftime("%Y年%m月%d日") + f"  {data.weekday}"
    y = text_bottom(draw, margin, y, date_line, title_font) + 12
    y = text_bottom(draw, margin, y, data.lunar_date, subtitle_font) + 8

    if data.jieqi_today:
        jieqi_line = f"今日节气 · {data.jieqi_today}"
    else:
        jieqi_line = f"下一个节气 · {data.next_jieqi_name}（{data.next_jieqi_date}）"
    y = text_bottom(draw, margin, y, jieqi_line, body_font) + 12
    y = draw_divider(draw, y + 12, width)

    y = draw_section_title(draw, margin, y, "倒计时", subtitle_font)
    if data.countdowns:
        for name, days in data.countdowns:
            y = text_bottom(draw, margin + 12, y, f"距离{name}  {days} 天", body_font) + 10
    else:
        y = text_bottom(draw, margin + 12, y, "暂无即将到来的节日", body_font) + 10
    y = draw_divider(draw, y + 8, width)

    y = text_bottom(draw, margin, y, config.CITY_NAME, weather_font) + 6
    y = text_bottom(draw, margin, y, f"{data.temperature}  {data.weather_text}", weather_font) + 12
    y = text_bottom(
        draw,
        margin,
        y,
        f"体感 {data.feels_like}   湿度 {data.humidity}",
        body_font,
    ) + 12
    y = text_bottom(draw, margin, y, data.rain_hint, body_font) + 12
    y = text_bottom(
        draw,
        margin,
        y,
        f"紫外线 {data.uv_level}   AQI {data.aqi} {data.aqi_category}",
        body_font,
    ) + 12
    y = draw_divider(draw, y + 12, width)

    y = draw_section_title(draw, margin, y, "近期节假日", subtitle_font)
    if data.upcoming_holidays:
        for line in data.upcoming_holidays:
            y = text_bottom(draw, margin + 12, y, f"· {line}", body_font) + 10
    else:
        y = text_bottom(draw, margin + 12, y, "未来120天暂无节假日", body_font) + 10

    if data.makeup_workdays:
        y += 8
        y = text_bottom(draw, margin + 12, y, "调休提醒", small_font) + 8
        for line in data.makeup_workdays:
            y = text_bottom(draw, margin + 12, y, f"· {line}", small_font) + 8

    updated = data.now.strftime("更新于 %H:%M")
    draw.text((margin, height - 56), updated, fill=120, font=small_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG", optimize=True)
    return output_path
