# bot.py
import logging
from aiogram import Bot, Dispatcher, executor
from config import BOT_TOKEN
from services.scheduler import start_scheduler
from handlers import register_handlers

logging.basicConfig(
    level=logging.INFO,
    filename="logs/bot.log",
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Регистрируем все обработчики
register_handlers(dp, bot)

async def on_startup(dp):
    # Запускаем планировщик, когда event loop уже запущен.
    start_scheduler(bot)
    logger.info("Бот запущен.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
