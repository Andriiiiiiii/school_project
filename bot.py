# bot.py
import logging
from aiogram import Bot, Dispatcher, executor
from config import BOT_TOKEN
from services.scheduler import start_scheduler
from handlers import register_handlers
import asyncio

logging.basicConfig(
    level=logging.INFO,
    filename="logs/bot.log",
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

register_handlers(dp, bot)

# Запускаем планировщик после старта event loop
async def on_startup(dp):
    loop = asyncio.get_running_loop()
    start_scheduler(bot, loop)
    logger.info("Бот запущен.")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
