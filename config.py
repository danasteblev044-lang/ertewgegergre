import os
from datetime import date

# Пытаемся загрузить .env через python-dotenv или вручную
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

# Telegram настройки
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMIN_ID = int(os.getenv("TELEGRAM_ADMIN_ID", "0")) if os.getenv("TELEGRAM_ADMIN_ID", "").isdigit() else None

# AI API настройки
PLUSVIBE_API_KEY = os.getenv("PLUSVIBE_API_KEY", "")
PLUSVIBE_BASE_URL = os.getenv("PLUSVIBE_BASE_URL", "https://plusvibeapi.ru/v1")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o")

# Majestic RP настройки
MAJESTIC_NICKNAME = os.getenv("MAJESTIC_NICKNAME", "Eskalane Helper")
MAJESTIC_FORUM_URL = os.getenv("MAJESTIC_FORUM_URL", "https://forum.majestic-rp.ru/forums/zhaloby-na-administratsiyu.1519/")

# Отсчет недели для расписания
# Текущая неделя (начиная с понедельника 12.10.2026) является числителем
ANCHOR_MONDAY = date.fromisoformat(os.getenv("ANCHOR_MONDAY", "2026-10-12"))
ANCHOR_WEEK_TYPE = os.getenv("ANCHOR_WEEK_TYPE", "числитель").lower()

# База данных SQLite
DB_PATH = os.path.join(os.path.dirname(__file__), "bot_data.db")
