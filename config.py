import os
from dotenv import load_dotenv

load_dotenv()

# Основные настройки
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_DEFAULT_TOKEN")
DB_PATH = os.getenv("DB_PATH", "bot.db")
LEVELS_DIR = os.getenv("LEVELS_DIR", "levels")
SERVER_TIMEZONE = os.getenv("SERVER_TIMEZONE", "UTC")

# Настройки уведомлений
REMINDER_DEFAULT = os.getenv("REMINDER_DEFAULT", "09:00:00")
REMINDER_START = os.getenv("REMINDER_START", "10:00")
DURATION_HOURS = float(os.getenv("DURATION_HOURS", 10))  # 10:00-20:00
DAILY_RESET_TIME = os.getenv("DAILY_RESET_TIME", "00:00")

# Настройки по умолчанию
DEFAULT_WORDS_PER_DAY = int(os.getenv("DEFAULT_WORDS_PER_DAY", 5))
DEFAULT_REPETITIONS = int(os.getenv("DEFAULT_REPETITIONS", 3))

# ЮKassa настройки
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")

# Цены подписки (в рублях)
SUBSCRIPTION_PRICES = {
    1: 299.00,    # 1 месяц
    3: 799.00,    # 3 месяца (скидка 11%)
    6: 1499.00,   # 6 месяцев (скидка 16%)
    12: 2899.00   # 12 месяцев (скидка 19%)
}

# Старая переменная для обратной совместимости
SUBSCRIPTION_PRICE = float(os.getenv("SUBSCRIPTION_PRICE", "299.00"))

# Наборы по умолчанию для каждого уровня
DEFAULT_SETS = {
    "A1": "A1 Basic 1",
    "A2": "A2 Basic 1", 
    "B1": "B1 Basic 1",
    "B2": "B2 Basic 1",
    "C1": "C1 Basic 1",
    "C2": "C2 Basic 1"
}

# Бесплатные наборы для каждого уровня
FREE_SETS = {
    "A1": ["A1 Basic 1"],
    "A2": ["A2 Basic 1"],
    "B1": ["B1 Basic 1"],
    "B2": ["B2 Basic 1"],
    "C1": ["C1 Basic 1"],
    "C2": ["C2 Basic 1"]
}

# Настройки для продакшена
PRODUCTION_MODE = os.getenv("PRODUCTION_MODE", "False").lower() == "true"
LOG_LEVEL = "WARNING" if PRODUCTION_MODE else "INFO"