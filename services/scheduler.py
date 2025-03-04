#services/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import asyncio
from aiogram import Bot
from zoneinfo import ZoneInfo
from database import crud
from utils.helpers import get_daily_words_for_user, daily_words_cache, daily_words_storage
from config import REMINDER_START, DURATION_HOURS, SERVER_TIMEZONE

FIRST_TIME = REMINDER_START

def scheduler_job(bot: Bot, loop: asyncio.AbstractEventLoop):
    """
    Функция, вызываемая каждые 60 секунд:
      - Для каждого пользователя текущее серверное время (с SERVER_TIMEZONE)
        переводится в его локальное время (на основе его поля timezone).
      - Если локальное время пользователя совпадает (час и минута)
        с одной из временных меток набора слов, отправляется уведомление.
      - Когда локальное время пользователя ровно совпадает с моментом (FIRST_TIME + DURATION_HOURS)
        (с точностью до минут) и набор слов еще не зафиксирован для данного дня,
        уникальные слова фиксируются в базу («Мой словарь»).
      - Набор слов дня обновляется только после наступления нового дня (00:00 локального времени).
    """
    now_server = datetime.now(tz=ZoneInfo(SERVER_TIMEZONE))
    users = crud.get_all_users()
    for user in users:
        chat_id = user[0]
        level = user[1]
        words_count = user[2]
        repetitions = user[3]
        user_tz = user[5] if len(user) > 5 and user[5] else "Europe/Moscow"
        now_local = now_server.astimezone(ZoneInfo(user_tz))
        now_local_str = now_local.strftime("%H:%M")
        local_today_str = now_local.strftime("%Y-%m-%d")
        
        local_base_obj = datetime.strptime(f"{local_today_str} {FIRST_TIME}", "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(user_tz))
        local_end_obj = local_base_obj + timedelta(hours=DURATION_HOURS)
        
        result = get_daily_words_for_user(chat_id, level, words_count, repetitions,
                                           first_time=FIRST_TIME, duration_hours=DURATION_HOURS)
        if result is None:
            continue
        messages, times = result
        
        if now_local_str in times:
            notif_index = times.index(now_local_str)
            message_text = messages[notif_index] if notif_index < len(messages) else ""
            asyncio.run_coroutine_threadsafe(
                bot.send_message(chat_id, f"📌 Слова дня:\n{message_text}"),
                loop
            )
        
        if now_local.hour == local_end_obj.hour and now_local.minute == local_end_obj.minute:
            if chat_id not in daily_words_storage or daily_words_storage[chat_id][0] != local_today_str:
                if chat_id in daily_words_cache:
                    _, messages, _, _, _, _, _, _ = daily_words_cache[chat_id]
                    unique_words = set(msg.replace("🔹 ", "") for msg in messages)
                    for word in unique_words:
                        crud.add_learned_word(chat_id, word, local_today_str)
                    daily_words_storage[chat_id] = daily_words_cache[chat_id]
        
        if now_local.hour == 0 and now_local.minute == 0:
            if chat_id in daily_words_cache:
                del daily_words_cache[chat_id]
            if chat_id in daily_words_storage:
                del daily_words_storage[chat_id]

def start_scheduler(bot: Bot, loop: asyncio.AbstractEventLoop):
    """
    Запускает планировщик APScheduler, который каждые 60 секунд вызывает scheduler_job.
    Параметры:
      bot - экземпляр бота
      loop - event loop бота
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(scheduler_job, 'interval', minutes=1, args=[bot, loop])
    scheduler.start()
    return scheduler
