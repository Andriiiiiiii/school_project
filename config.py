import os
from dotenv import load_dotenv

load_dotenv()  # Загружает переменные из файла .env

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_DEFAULT_TOKEN")
DB_PATH = os.getenv("DB_PATH", "bot.db")
LEVELS_DIR = os.getenv("LEVELS_DIR", "levels")
REMINDER_DEFAULT = os.getenv("REMINDER_DEFAULT", "09:00:00")
REMINDER_START = os.getenv("REMINDER_START", "10:00")  # Формат "HH:MM" или "HH:MM:SS"
DURATION_HOURS = float(os.getenv("DURATION_HOURS", 10))
DEFAULT_WORDS_PER_DAY = int(os.getenv("DEFAULT_WORDS_PER_DAY", 5))
DEFAULT_REPETITIONS = int(os.getenv("DEFAULT_REPETITIONS", 3))
SERVER_TIMEZONE = os.getenv("SERVER_TIMEZONE", "UTC")
DAILY_RESET_TIME = os.getenv("DAILY_RESET_TIME", "00:00")

# Основные сеты для каждого уровня
DEFAULT_SETS = {
    "A1": "At Home",
    "A2": "Describing People",
    "B1": "Art, Music & Culture",
    "B2": "Science & Innovation",
    "C1": "Academic & Formal English",
    "C2": "Advanced Academic Writing"
}
