import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Panel API
PANEL_URL = os.getenv("PANEL_URL", "https://ru-panel.konoha.us.ci:23168/229XmnXsbkeTr8J7Xr")
SUB_URL = os.getenv("SUB_URL", "https://ru-panel.konoha.us.ci:2096")
SUB_PATH = os.getenv("SUB_PATH", "gdfhskjlfsdfgn")
XUI_TOKEN = os.getenv("XUI_TOKEN")

# Tariffs
TARIFFS = {
    "trial": {
        "name": "Пробный период",
        "days": 3,
        "price": 0,
        "group": "Trial",  # ← исправлено: Trial вместо users
        "description": "3 дня бесплатно"
    },
    "monthly": {
        "name": "1 месяц",
        "days": 30,
        "price": 1,
        "group": "Monthly",
        "description": "30 дней доступа"
    },
    "quarterly": {
        "name": "3 месяца",
        "days": 90,
        "price": 2,
        "group": "Quarterly",
        "description": "90 дней доступа"
    }
}

# Database
DATABASE_URL = "sqlite:///vpn_bot.db"