# config.py
import os
from dotenv import load_dotenv

load_dotenv()  # Загружает переменные из файла .env

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_DEFAULT_TOKEN")
DB_PATH = os.getenv("DB_PATH", "bot.db")
LEVELS_DIR = os.getenv("LEVELS_DIR", "levels")
REMINDER_DEFAULT = os.getenv("REMINDER_DEFAULT", "09:00")
# Настройки по умолчанию для тестирования, уведомлений и количества слов:
DEFAULT_WORDS_PER_DAY = int(os.getenv("DEFAULT_WORDS_PER_DAY", 5))
DEFAULT_NOTIFICATIONS = int(os.getenv("DEFAULT_NOTIFICATIONS", 10))
