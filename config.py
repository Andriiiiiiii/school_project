#config.py
import os
from dotenv import load_dotenv

load_dotenv()  # Загружает переменные из файла .env

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_DEFAULT_TOKEN")
DB_PATH = os.getenv("DB_PATH", "bot.db")
LEVELS_DIR = os.getenv("LEVELS_DIR", "levels")
REMINDER_DEFAULT = os.getenv("REMINDER_DEFAULT", "09:00:00")
REMINDER_START = os.getenv("REMINDER_START", "16:00")  # Формат "HH:MM" или "HH:MM:SS"
DURATION_HOURS = float(os.getenv("DURATION_HOURS", 1))  # Например, 1 или 3 часов
DEFAULT_WORDS_PER_DAY = int(os.getenv("DEFAULT_WORDS_PER_DAY", 10))
DEFAULT_REPETITIONS = int(os.getenv("DEFAULT_REPETITIONS", 3))  # Количество повторений слов в день
SERVER_TIMEZONE = os.getenv("SERVER_TIMEZONE", "UTC")  # Часовой пояс сервера
