from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import config
from data_sources import DashboardData


def find_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        config.FONT_PATH,
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    ]

    for path in candidates:
        if not path:
            continue
        font_path = Path(path)
        if font_path.exists():
            return ImageFont.truetype(str(font_path), size=size)

    return ImageFont.load_default()


def draw_section_title(draw: ImageDraw.ImageDraw, x: int, y: int, title: str, font) -> int:
    draw.text((x, y), title, fill=0, font=font)
    return y + font.size + 18


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
    hero_font = find_font(64)

    margin = 56
    y = 48

    date_line = data.now.strftime("%Y年%m月%d日") + f"  {data.weekday}"
    draw.text((margin, y), date_line, fill=0, font=title_font)
    y += title_font.size + 12

    draw.text((margin, y), data.lunar_date, fill=0, font=subtitle_font)
    y += subtitle_font.size + 8

    if data.jieqi_today:
        jieqi_line = f"今日节气 · {data.jieqi_today}"
    else:
        jieqi_line = f"下一个节气 · {data.next_jieqi_name}（{data.next_jieqi_date}）"
    draw.text((margin, y), jieqi_line, fill=0, font=body_font)
    y = draw_divider(draw, y + 24, width)

    y = draw_section_title(draw, margin, y, "倒计时", subtitle_font)
    if data.countdowns:
        for name, days in data.countdowns:
            draw.text((margin + 12, y), f"距离{name}  {days} 天", fill=0, font=body_font)
            y += body_font.size + 10
    else:
        draw.text((margin + 12, y), "暂无即将到来的节日", fill=0, font=body_font)
        y += body_font.size + 10
    y = draw_divider(draw, y + 8, width)

    weather_title = f"{config.CITY_NAME}  {data.temperature}  {data.weather_text}"
    draw.text((margin, y), weather_title, fill=0, font=hero_font)
    y += hero_font.size + 10

    draw.text(
        (margin, y),
        f"体感 {data.feels_like}   湿度 {data.humidity}",
        fill=0,
        font=body_font,
    )
    y += body_font.size + 12
    draw.text((margin, y), data.rain_hint, fill=0, font=body_font)
    y += body_font.size + 12
    draw.text(
        (margin, y),
        f"紫外线 {data.uv_level}   AQI {data.aqi} {data.aqi_category}",
        fill=0,
        font=body_font,
    )
    y = draw_divider(draw, y + 24, width)

    y = draw_section_title(draw, margin, y, "近期节假日", subtitle_font)
    if data.upcoming_holidays:
        for line in data.upcoming_holidays:
            draw.text((margin + 12, y), f"· {line}", fill=0, font=body_font)
            y += body_font.size + 10
    else:
        draw.text((margin + 12, y), "未来120天暂无节假日", fill=0, font=body_font)
        y += body_font.size + 10

    if data.makeup_workdays:
        y += 8
        draw.text((margin + 12, y), "调休提醒", fill=0, font=small_font)
        y += small_font.size + 8
        for line in data.makeup_workdays:
            draw.text((margin + 12, y), f"· {line}", fill=0, font=small_font)
            y += small_font.size + 8

    updated = data.now.strftime("更新于 %H:%M")
    draw.text((margin, height - 56), updated, fill=120, font=small_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG", optimize=True)
    return output_path
