import os
from dotenv import load_dotenv

load_dotenv()  # Загружает переменные из файла .env

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_DEFAULT_TOKEN")
DB_PATH = os.getenv("DB_PATH", "bot.db")
LEVELS_DIR = os.getenv("LEVELS_DIR", "levels")
REMINDER_DEFAULT = os.getenv("REMINDER_DEFAULT", "09:00:00")
REMINDER_START = os.getenv("REMINDER_START", "10:00")  # Формат "HH:MM" или "HH:MM:SS" - ИЗМЕНЕНО для 10:00
DURATION_HOURS = float(os.getenv("DURATION_HOURS", 10)) # ИЗМЕНЕНО на 10 часов (с 10:00 до 20:00)
DEFAULT_WORDS_PER_DAY = int(os.getenv("DEFAULT_WORDS_PER_DAY", 5))
DEFAULT_REPETITIONS = int(os.getenv("DEFAULT_REPETITIONS", 3))
SERVER_TIMEZONE = os.getenv("SERVER_TIMEZONE", "UTC")
DAILY_RESET_TIME = os.getenv("DAILY_RESET_TIME", "00:00")

# ЮKassa настройки
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
SUBSCRIPTION_PRICE = float(os.getenv("SUBSCRIPTION_PRICE", "299.00"))  # рублей в месяц

# Основные сеты для каждого уровня
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
    "A1": ["A1 Basic 1", "A1 Basic 2"],
    "A2": ["A2 Basic 1", "A2 Basic 2"],
    "B1": ["B1 Basic 1", "B1 Basic 2"],
    "B2": ["B2 Basic 1", "B2 Basic 2"],
    "C1": ["C1 Basic 1", "C1 Basic 2"],
    "C2": ["C2 Basic 1", "C2 Basic 2"]
}