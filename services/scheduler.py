# services/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import asyncio

def send_daily_words(bot):
    from database import crud
    # Получаем всех пользователей
    from database.db import cursor
    cursor.execute("SELECT chat_id, reminder_time FROM users")
    users = cursor.fetchall()
    now = datetime.now().strftime("%H:%M")
    for user in users:
        chat_id, reminder_time = user
        if now == reminder_time:
            asyncio.create_task(send_word(bot, chat_id))

async def send_word(bot, chat_id):
    from handlers.words import send_proficiency_word_of_day
    await send_proficiency_word_of_day(chat_id, bot)

def start_scheduler(bot):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_daily_words, 'interval', minutes=1, args=[bot])
    scheduler.start()
    return scheduler
