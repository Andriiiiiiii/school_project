#pathtofile/services/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import asyncio
from aiogram import Bot
from zoneinfo import ZoneInfo
from database import crud
from utils.helpers import get_daily_words_for_user, daily_words_cache, daily_words_storage
from config import REMINDER_START, DURATION_HOURS, SERVER_TIMEZONE

FIRST_TIME = REMINDER_START  # Интервал начинается в REMINDER_START

def scheduler_job(bot: Bot, loop: asyncio.AbstractEventLoop):
    """
    Вызывается каждые 60 секунд:
      - Для каждого пользователя текущее серверное время (SERVER_TIMEZONE) переводится в его локальное время.
      - Если локальное время пользователя совпадает (час и минута) с одной из временных меток набора слов,
        отправляется уведомление.
      - Если локальное время пользователя ровно совпадает с моментом (FIRST_TIME + DURATION_HOURS) (с точностью до минут),
        и набор слов ещё не зафиксирован для этого дня, то уникальные слова фиксируются в базу («Мой словарь»).
      - Набор слов дня обновляется только после наступления нового дня (00:00 локального времени).
    """
    # Текущее время сервера с часовым поясом SERVER_TIMEZONE
    now_server = datetime.now(tz=ZoneInfo(SERVER_TIMEZONE))
    users = crud.get_all_users()
    for user in users:
        chat_id = user[0]
        level = user[1]
        words_count = user[2]
        repetitions = user[3]
        # Получаем часовой пояс пользователя (если не задан, используем "Europe/Moscow")
        user_tz = user[5] if len(user) > 5 and user[5] else "Europe/Moscow"
        # Переводим серверное время в локальное время пользователя
        now_local = now_server.astimezone(ZoneInfo(user_tz))
        now_local_str = now_local.strftime("%H:%M")
        local_today_str = now_local.strftime("%Y-%m-%d")
        
        # Вычисляем локальное время начала и окончания интервала уведомлений
        local_base_obj = datetime.strptime(f"{local_today_str} {FIRST_TIME}", "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(user_tz))
        local_end_obj = local_base_obj + timedelta(hours=DURATION_HOURS)
        
        # Получаем набор слов (из кэша или генерируем новый)
        result = get_daily_words_for_user(chat_id, level, words_count, repetitions,
                                           first_time=FIRST_TIME, duration_hours=DURATION_HOURS)
        if result is None:
            continue
        messages, times = result
        
        # Отправляем уведомление, если локальное время совпадает с одной из рассчитанных меток
        if now_local_str in times:
            notif_index = times.index(now_local_str)
            message_text = messages[notif_index] if notif_index < len(messages) else ""
            asyncio.run_coroutine_threadsafe(
                bot.send_message(chat_id, f"📌 Слова дня:\n{message_text}"),
                loop
            )
        
        # Фиксируем набор слов ровно в момент, когда локальное время пользователя совпадает с local_end_obj (по часам и минутам)
        if now_local.hour == local_end_obj.hour and now_local.minute == local_end_obj.minute:
            # Фиксируем набор, если он ещё не был зафиксирован для данного пользователя сегодня
            if chat_id not in daily_words_storage or daily_words_storage[chat_id][0] != local_today_str:
                if chat_id in daily_words_cache:
                    _, messages, _, _, _, _, _, _ = daily_words_cache[chat_id]
                    unique_words = set(msg.replace("🔹 ", "") for msg in messages)
                    for word in unique_words:
                        crud.add_learned_word(chat_id, word, local_today_str)
                    daily_words_storage[chat_id] = daily_words_cache[chat_id]
                    # Не удаляем запись из daily_words_cache, чтобы при обращении сначала проверялось daily_words_storage

        # Если наступило новое утро (00:00 локального времени), очищаем кэш и фиксированное хранилище для данного пользователя
        if now_local.hour == 0 and now_local.minute == 0:
            if chat_id in daily_words_cache:
                del daily_words_cache[chat_id]
            if chat_id in daily_words_storage:
                del daily_words_storage[chat_id]

def start_scheduler(bot: Bot, loop: asyncio.AbstractEventLoop):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(scheduler_job, 'interval', minutes=1, args=[bot, loop])
    scheduler.start()
    return scheduler
