# config.py
import os
from dotenv import load_dotenv

load_dotenv()  # Загружаем переменные из .env

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_DEFAULT_TOKEN")
DB_PATH = os.getenv("DB_PATH", "bot.db")
LEVELS_DIR = os.getenv("LEVELS_DIR", "levels")
REMINDER_DEFAULT = os.getenv("REMINDER_DEFAULT", "09:00")
