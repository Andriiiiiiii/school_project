# services/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import asyncio
from aiogram import Bot
from zoneinfo import ZoneInfo
from database import crud
from utils.helpers import get_daily_words_for_user, daily_words_cache, reset_daily_words_cache, previous_daily_words
from config import REMINDER_START, DURATION_HOURS, SERVER_TIMEZONE, DAILY_RESET_TIME

FIRST_TIME = REMINDER_START

# Словарь для отслеживания, было ли отправлено напоминание по квизу для каждого пользователя за текущий день
quiz_reminder_sent = {}

def scheduler_job(bot: Bot, loop: asyncio.AbstractEventLoop):
    """
    Функция, вызываемая каждые 60 секунд:
      - Переводит серверное время в локальное время пользователя.
      - Если текущее локальное время совпадает с одной из временных меток уведомлений, отправляет уведомление слова дня.
      - Если текущее локальное время совпадает с моментом (FIRST_TIME + DURATION_HOURS),
        отправляет уведомление "Пройдите квиз чтобы слова добавились в Мой словарь",
        если оно еще не было отправлено сегодня.
      - Если локальное время совпадает с DAILY_RESET_TIME, сохраняет текущий список уникальных слов
        в previous_daily_words и сбрасывает кэш.
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
        
        # Вычисляем базовое локальное время начала и окончания периода
        local_base_obj = datetime.strptime(f"{local_today_str} {FIRST_TIME}", "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(user_tz))
        local_end_obj = local_base_obj + timedelta(hours=DURATION_HOURS)
        end_time_str = local_end_obj.strftime("%H:%M")
        
        # Получаем список слов дня (это также обновляет кэш, если необходимо)
        result = get_daily_words_for_user(chat_id, level, words_count, repetitions,
                                           first_time=FIRST_TIME, duration_hours=DURATION_HOURS)
        if result is None:
            continue
        messages, times = result

        # Отправка обычных уведомлений по расписанию
        if now_local_str in times:
            notif_index = times.index(now_local_str)
            message_text = messages[notif_index] if notif_index < len(messages) else ""
            asyncio.run_coroutine_threadsafe(
                bot.send_message(chat_id, f"📌 Слова дня:\n{message_text}"),
                loop
            )
        
        # Если текущее время равно концу периода (FIRST_TIME + DURATION_HOURS)
        if now_local_str == end_time_str:
            # Проверяем, было ли уже отправлено уведомление для данного пользователя сегодня
            if quiz_reminder_sent.get(chat_id) != local_today_str:
                asyncio.run_coroutine_threadsafe(
                    bot.send_message(chat_id, "Пройдите квиз чтобы слова добавились в Мой словарь"),
                    loop
                )
                quiz_reminder_sent[chat_id] = local_today_str

        # При наступлении DAILY_RESET_TIME сбрасываем кэш и сохраняем текущий список уникальных слов
        if now_local.strftime("%H:%M") == DAILY_RESET_TIME:
            if chat_id in daily_words_cache:
                entry = daily_words_cache[chat_id]
                unique_words = entry[8]  # список уникальных слов текущего дня
                # Фильтруем, чтобы оставить только те слова, которых еще нет в "Моем словаре"
                learned_raw = crud.get_learned_words(chat_id)
                learned_set = set(item[0] for item in learned_raw)
                filtered_unique = [w for w in unique_words if w not in learned_set]
                previous_daily_words[chat_id] = filtered_unique
                reset_daily_words_cache(chat_id)
            # Сбрасываем флаг напоминания, чтобы уведомление отправлялось для нового дня
            if chat_id in quiz_reminder_sent:
                del quiz_reminder_sent[chat_id]

def start_scheduler(bot: Bot, loop: asyncio.AbstractEventLoop):
    """
    Запускает APScheduler, который каждые 60 секунд вызывает scheduler_job.
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(scheduler_job, 'interval', minutes=1, args=[bot, loop])
    scheduler.start()
    return scheduler
