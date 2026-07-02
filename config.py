import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
OUTPUT_FILE = OUTPUT_DIR / "dashboard.png"

# Kindle resolution (adjust after checking `eips -i` on device)
WIDTH = int(os.environ.get("KINDLE_WIDTH", "1072"))
HEIGHT = int(os.environ.get("KINDLE_HEIGHT", "1448"))

# Shanghai
LOCATION_ID = os.environ.get("QWEATHER_LOCATION_ID", "101020100")
LATITUDE = os.environ.get("QWEATHER_LAT", "31.23")
LONGITUDE = os.environ.get("QWEATHER_LON", "121.47")
CITY_NAME = os.environ.get("CITY_NAME", "上海")

# QWeather
API_HOST = os.environ.get("QWEATHER_API_HOST", "").rstrip("/")
JWT_TOKEN = os.environ.get("QWEATHER_JWT", "")
KID = os.environ.get("QWEATHER_KID", "")
PROJECT_ID = os.environ.get("QWEATHER_PROJECT_ID", "")
PRIVATE_KEY = os.environ.get("QWEATHER_PRIVATE_KEY", "")

# Holiday data CDN
HOLIDAY_CDN = "https://cdn.jsdelivr.net/gh/NateScarlet/holiday-cn@master"

# Font (auto-detected if empty)
FONT_PATH = os.environ.get("FONT_PATH", "")

# Display timezone
TIMEZONE = os.environ.get("TZ", "Asia/Shanghai")
