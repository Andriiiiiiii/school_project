# bot.py
import logging
from aiogram import Bot, Dispatcher, executor
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import handlers
import database

# Замените эту строку на токен вашего бота, полученный от BotFather
BOT_TOKEN = '7826920570:AAFNCinJxjrYMt_a_MWhYVNyYPRQKu0ELzg'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

handlers.register_handlers(dp, bot)

scheduler = AsyncIOScheduler()
# Планируем авторассылку слова дня каждую минуту
scheduler.add_job(handlers.check_and_send_daily_words, 'interval', minutes=1, args=[bot])

async def on_startup(dp):
    scheduler.start()
    logger.info("Планировщик запущен.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
