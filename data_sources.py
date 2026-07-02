from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import requests
from lunar_python import Solar

import auth
import config


@dataclass
class DashboardData:
    now: datetime
    weekday: str
    lunar_date: str
    jieqi_today: str
    next_jieqi_name: str
    next_jieqi_date: str
    countdowns: list[tuple[str, int]]
    weather_text: str
    temperature: str
    feels_like: str
    humidity: str
    rain_hint: str
    uv_level: str
    aqi: str
    aqi_category: str
    upcoming_holidays: list[str]
    makeup_workdays: list[str]


WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

COUNTDOWN_TARGETS = ["春节", "国庆", "中秋", "元旦", "清明", "端午", "劳动节"]


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
        days.extend(fetch_holiday_year(year))
    return days


def build_countdowns(today: date, holidays: list[dict[str, Any]]) -> list[tuple[str, int]]:
    results: list[tuple[str, int]] = []
    seen: set[str] = set()

    for target in COUNTDOWN_TARGETS:
        for item in holidays:
            name = item.get("name", "")
            if target not in name or not item.get("isOffDay"):
                continue
            holiday_date = date.fromisoformat(item["date"])
            if holiday_date < today:
                continue
            if target in seen:
                break
            seen.add(target)
            results.append((target, (holiday_date - today).days))
            break

    results.sort(key=lambda x: x[1])
    return results[:3]


def build_upcoming_holidays(today: date, holidays: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    upcoming: list[str] = []
    makeup: list[str] = []

    for item in holidays:
        holiday_date = date.fromisoformat(item["date"])
        if holiday_date < today:
            continue
        if holiday_date > today + timedelta(days=120):
            continue

        name = item.get("name", "")
        weekday_short = "一二三四五六日"[holiday_date.weekday()]
        line = f"{holiday_date.month}月{holiday_date.day}日 {name}"

        if item.get("isOffDay"):
            if len(upcoming) < 4:
                upcoming.append(line)
        else:
            if len(makeup) < 2:
                makeup.append(f"{holiday_date.month}月{holiday_date.day}日(周{weekday_short}) 补班")

    return upcoming, makeup


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
                return f"{hour.get('fxTime', '')[-5:]} 起{text}"
    except Exception:
        pass

    return "未来2小时无明显降水"


def fetch_uv() -> str:
    data = _get("/v7/indices/1d", {"location": config.LOCATION_ID, "type": "5"})
    daily = data.get("daily", [])
    if not daily:
        return "--"
    item = daily[0]
    return f"{item.get('category', '--')} ({item.get('level', '--')}级)"


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
    now = datetime.now()
    today = now.date()
    holidays = load_holidays(today)

    lunar_date, jieqi_today, next_jieqi_name, next_jieqi_date = get_calendar_info(today)
    countdowns = build_countdowns(today, holidays)
    upcoming_holidays, makeup_workdays = build_upcoming_holidays(today, holidays)

    weather_text, temperature, feels_like, humidity = fetch_weather()
    rain_hint = fetch_rain_hint()
    uv_level = fetch_uv()
    aqi, aqi_category = fetch_aqi()

    return DashboardData(
        now=now,
        weekday=WEEKDAYS[today.weekday()],
        lunar_date=lunar_date,
        jieqi_today=jieqi_today,
        next_jieqi_name=next_jieqi_name,
        next_jieqi_date=next_jieqi_date,
        countdowns=countdowns,
        weather_text=weather_text,
        temperature=temperature,
        feels_like=feels_like,
        humidity=humidity,
        rain_hint=rain_hint,
        uv_level=uv_level,
        aqi=aqi,
        aqi_category=aqi_category,
        upcoming_holidays=upcoming_holidays,
        makeup_workdays=makeup_workdays,
    )
