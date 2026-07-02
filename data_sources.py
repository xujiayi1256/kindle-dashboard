from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import requests
from lunar_python import Lunar, Solar

import auth
import config


@dataclass
class HolidayItem:
    name: str
    days_until: int
    date_range: str
    off_days: int
    is_estimate: bool


@dataclass
class DashboardData:
    now: datetime
    weekday: str
    lunar_date: str
    jieqi_today: str
    next_jieqi_name: str
    next_jieqi_date: str
    holiday_items: list[HolidayItem]
    weather_text: str
    temperature: str
    feels_like: str
    humidity: str
    rain_hint: str
    rain_alert: bool
    tomorrow_weather: str
    uv_level: str
    aqi: str
    aqi_category: str
    makeup_workdays: list[str]


WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def now_in_shanghai() -> datetime:
    return datetime.now(ZoneInfo(config.TIMEZONE))


def _headers() -> dict[str, str]:
    if not config.API_HOST:
        raise RuntimeError("QWEATHER_API_HOST is not set.")
    return {"Authorization": f"Bearer {auth.get_qweather_token()}"}


def _get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{config.API_HOST}{path}"
    response = requests.get(url, headers=_headers(), params=params, timeout=20)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict) and data.get("code") not in (None, "200", 200):
        raise RuntimeError(f"QWeather error for {path}: {data}")
    return data


def fetch_holiday_year(year: int) -> list[dict[str, Any]]:
    url = f"{config.HOLIDAY_CDN}/{year}.json"
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    payload = response.json()
    return payload.get("days", [])


def load_holidays(today: date) -> list[dict[str, Any]]:
    years = {today.year, today.year + 1}
    days: list[dict[str, Any]] = []
    for year in sorted(years):
        try:
            days.extend(fetch_holiday_year(year))
        except requests.RequestException:
            continue
    return days


def get_lunar_spring_festival_date(today: date) -> date:
    """Next lunar 正月初一 (Spring Festival) by astronomical calendar."""
    lunar_year = Solar.fromYmd(today.year, today.month, today.day).getLunar().getYear()
    spring_solar = Lunar.fromYmd(lunar_year, 1, 1).getSolar()
    spring_date = date(spring_solar.getYear(), spring_solar.getMonth(), spring_solar.getDay())
    if spring_date < today:
        spring_solar = Lunar.fromYmd(lunar_year + 1, 1, 1).getSolar()
        spring_date = date(spring_solar.getYear(), spring_solar.getMonth(), spring_solar.getDay())
    return spring_date


def short_holiday_name(name: str) -> str:
    name = normalize_holiday_name(name)
    if name.endswith("节") and len(name) > 2:
        return name[:-1]
    return name


def collect_off_day_groups(holidays: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in holidays:
        holiday_date = date.fromisoformat(item["date"])
        if holiday_date < today or holiday_date > today + timedelta(days=120):
            continue
        if not item.get("isOffDay"):
            continue
        items.append({"date": holiday_date, "name": normalize_holiday_name(item.get("name", ""))})

    items.sort(key=lambda x: x["date"])
    groups: list[dict[str, Any]] = []
    for item in items:
        if (
            groups
            and groups[-1]["name"] == item["name"]
            and (item["date"] - groups[-1]["end"]).days == 1
        ):
            groups[-1]["end"] = item["date"]
        else:
            groups.append({"name": item["name"], "start": item["date"], "end": item["date"]})
    return groups


def build_holiday_overview(
    today: date, holidays: list[dict[str, Any]]
) -> tuple[list[HolidayItem], list[str]]:
    items: list[HolidayItem] = []
    for group in collect_off_day_groups(holidays, today):
        start = group["start"]
        end = group["end"]
        off_days = (end - start).days + 1
        items.append(
            HolidayItem(
                name=short_holiday_name(group["name"]),
                days_until=(start - today).days,
                date_range=format_date_range(start, end),
                off_days=off_days,
                is_estimate=False,
            )
        )

    if not any("春节" in item.name for item in items):
        spring_date = get_lunar_spring_festival_date(today)
        items.append(
            HolidayItem(
                name="春节",
                days_until=(spring_date - today).days,
                date_range=f"{spring_date.month}月{spring_date.day}日",
                off_days=1,
                is_estimate=True,
            )
        )

    items.sort(key=lambda x: x.days_until)
    if items:
        nearest_days = items[0].days_until
        max_gap = 45
        items = [item for item in items if item.days_until <= nearest_days + max_gap][:3]

    makeup = group_holiday_ranges(holidays, today, off_day=False, limit=3)
    return items, makeup


def normalize_holiday_name(name: str) -> str:
    for token in ("（休）", "(休)", "补班", "（班）", "(班)"):
        name = name.replace(token, "")
    return name.strip()


def format_date_range(start: date, end: date) -> str:
    if start == end:
        return f"{start.month}月{start.day}日"
    if start.month == end.month:
        return f"{start.month}月{start.day}日-{end.day}日"
    return f"{start.month}月{start.day}日-{end.month}月{end.day}日"


def group_holiday_ranges(
    holidays: list[dict[str, Any]],
    today: date,
    *,
    off_day: bool,
    limit: int,
) -> list[str]:
    items: list[dict[str, Any]] = []
    for item in holidays:
        holiday_date = date.fromisoformat(item["date"])
        if holiday_date < today or holiday_date > today + timedelta(days=120):
            continue
        if bool(item.get("isOffDay")) != off_day:
            continue
        items.append({"date": holiday_date, "name": normalize_holiday_name(item.get("name", ""))})

    items.sort(key=lambda x: x["date"])
    groups: list[dict[str, Any]] = []
    for item in items:
        if (
            groups
            and groups[-1]["name"] == item["name"]
            and (item["date"] - groups[-1]["end"]).days == 1
        ):
            groups[-1]["end"] = item["date"]
        else:
            groups.append({"name": item["name"], "start": item["date"], "end": item["date"]})

    lines: list[str] = []
    for group in groups[:limit]:
        date_text = format_date_range(group["start"], group["end"])
        day_count = (group["end"] - group["start"]).days + 1
        if off_day and day_count > 1:
            lines.append(f"{date_text} {group['name']}（休{day_count}天）")
        elif off_day:
            lines.append(f"{date_text} {group['name']}")
        else:
            weekday_short = "一二三四五六日"[group["start"].weekday()]
            lines.append(f"{date_text}(周{weekday_short}) 补班")
    return lines



def get_calendar_info(today: date) -> tuple[str, str, str, str]:
    solar = Solar.fromYmd(today.year, today.month, today.day)
    lunar = solar.getLunar()

    lunar_date = f"农历{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}"

    jieqi_today = lunar.getJieQi() or ""
    next_jieqi = lunar.getNextJieQi()
    next_solar = next_jieqi.getSolar()
    next_jieqi_date = f"{next_solar.getMonth()}月{next_solar.getDay()}日"

    return lunar_date, jieqi_today, next_jieqi.getName(), next_jieqi_date


def fetch_weather() -> tuple[str, str, str, str]:
    data = _get("/v7/weather/now", {"location": config.LOCATION_ID})
    now = data["now"]
    return (
        now.get("text", "--"),
        f"{now.get('temp', '--')}°C",
        f"{now.get('feelsLike', '--')}°C",
        f"{now.get('humidity', '--')}%",
    )


def _format_daily_weather(day: dict[str, Any]) -> str:
    temp_min = day.get("tempMin", "--")
    temp_max = day.get("tempMax", "--")
    text_day = day.get("textDay", "")
    text_night = day.get("textNight", "")
    if text_day and text_night and text_day != text_night:
        weather_text = f"{text_day}转{text_night}"
    else:
        weather_text = text_day or text_night or "--"
    return f"明日  {temp_min}~{temp_max}°C  {weather_text}"


def fetch_tomorrow_weather(today: date) -> str:
    try:
        data = _get("/v7/weather/3d", {"location": config.LOCATION_ID})
        tomorrow = (today + timedelta(days=1)).isoformat()
        for day in data.get("daily", []):
            if day.get("fxDate") == tomorrow:
                return _format_daily_weather(day)

        daily = data.get("daily", [])
        if len(daily) >= 2 and daily[0].get("fxDate") == today.isoformat():
            return _format_daily_weather(daily[1])
    except Exception:
        pass
    return "明日天气预报暂无"


def fetch_rain_hint() -> str:
    try:
        data = _get(
            "/v7/minutely/5m",
            {"location": f"{config.LONGITUDE},{config.LATITUDE}"},
        )
        summary = data.get("summary", "")
        if summary:
            return summary
    except Exception:
        pass

    try:
        data = _get("/v7/weather/24h", {"location": config.LOCATION_ID})
        for hour in data.get("hourly", [])[:6]:
            text = hour.get("text", "")
            if "雨" in text:
                fx_time = hour.get("fxTime", "")
                time_text = fx_time[11:16] if len(fx_time) >= 16 else fx_time[-5:]
                return f"{time_text} 起{text}"
    except Exception:
        pass

    return "未来2小时无明显降水"


def is_rainy(weather_text: str, rain_hint: str) -> bool:
    if any(keyword in weather_text for keyword in ("雨", "雪", "霰")):
        return True
    if any(token in rain_hint for token in ("无明显降水", "无降水", "不会下雨", "雨就停了")):
        return "雨" in rain_hint
    return "雨" in rain_hint or "雪" in rain_hint


def build_rain_display(weather_text: str, rain_hint: str) -> tuple[str, bool]:
    rainy = is_rainy(weather_text, rain_hint)
    if not rainy:
        return rain_hint, False

    hint = rain_hint
    if "伞" not in hint:
        hint = f"{hint}  ·  记得带伞"
    return hint, True


def fetch_uv() -> str:
    data = _get("/v7/indices/1d", {"location": config.LOCATION_ID, "type": "5"})
    daily = data.get("daily", [])
    if not daily:
        return "--"
    item = daily[0]
    return str(item.get("category", "--"))


def fetch_aqi() -> tuple[str, str]:
    data = _get(f"/airquality/v1/current/{config.LATITUDE}/{config.LONGITUDE}")
    indexes = data.get("indexes", [])
    for index in indexes:
        code = index.get("code", "")
        if code in ("cn-mee", "qaqi", "us-epa") or "aqi" in code.lower():
            aqi = index.get("aqiDisplay") or index.get("aqi") or "--"
            category = index.get("category") or index.get("level") or "--"
            return str(aqi), str(category)

    if indexes:
        first = indexes[0]
        return str(first.get("aqiDisplay", "--")), str(first.get("category", "--"))

    return "--", "--"


def collect_dashboard_data() -> DashboardData:
    now = now_in_shanghai()
    today = now.date()
    holidays = load_holidays(today)

    lunar_date, jieqi_today, next_jieqi_name, next_jieqi_date = get_calendar_info(today)
    holiday_items, makeup_workdays = build_holiday_overview(today, holidays)

    weather_text, temperature, feels_like, humidity = fetch_weather()
    raw_rain_hint = fetch_rain_hint()
    rain_hint, rain_alert = build_rain_display(weather_text, raw_rain_hint)
    tomorrow_weather = fetch_tomorrow_weather(today)
    uv_level = fetch_uv()
    aqi, aqi_category = fetch_aqi()

    return DashboardData(
        now=now,
        weekday=WEEKDAYS[today.weekday()],
        lunar_date=lunar_date,
        jieqi_today=jieqi_today,
        next_jieqi_name=next_jieqi_name,
        next_jieqi_date=next_jieqi_date,
        holiday_items=holiday_items,
        weather_text=weather_text,
        temperature=temperature,
        feels_like=feels_like,
        humidity=humidity,
        rain_hint=rain_hint,
        rain_alert=rain_alert,
        tomorrow_weather=tomorrow_weather,
        uv_level=uv_level,
        aqi=aqi,
        aqi_category=aqi_category,
        makeup_workdays=makeup_workdays,
    )
