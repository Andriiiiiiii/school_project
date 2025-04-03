# services/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import asyncio
import logging
from aiogram import Bot
from zoneinfo import ZoneInfo
from database import crud
from utils.helpers import get_daily_words_for_user, daily_words_manager, previous_daily_words_manager, reset_daily_words_cache
from config import REMINDER_START, DURATION_HOURS, SERVER_TIMEZONE, DAILY_RESET_TIME

logger = logging.getLogger(__name__)
FIRST_TIME = REMINDER_START

# Словарь для отслеживания, было ли отправлено напоминание по квизу для каждого пользователя за текущий день
quiz_reminder_sent = {}

def scheduler_job(bot: Bot, loop: asyncio.AbstractEventLoop):
    """
    Функция, вызываемая каждые 60 секунд.
    """
    try:
        # Получаем серверное время с установленной временной зоной
        try:
            now_server = datetime.now(tz=ZoneInfo(SERVER_TIMEZONE))
        except Exception as e:
            logger.error(f"Ошибка при установке серверной временной зоны {SERVER_TIMEZONE}: {e}")
            now_server = datetime.now(tz=ZoneInfo("UTC"))  # Используем UTC как запасной вариант
        
        # Получаем всех пользователей
        try:
            users = crud.get_all_users()
        except Exception as e:
            logger.error(f"Error getting users from database: {e}")
            users = []
            
        for user in users:
            try:
                process_user(user, now_server, bot, loop)
            except Exception as e:
                logger.error(f"Error processing user {user[0] if user else 'unknown'}: {e}")
                continue
    except Exception as e:
        logger.error(f"Unhandled error in scheduler_job: {e}")

def process_user(user, now_server, bot, loop):
    """
    Обрабатывает одного пользователя в планировщике.
    Вынесено в отдельную функцию для лучшей изоляции ошибок.
    """
    chat_id = user[0]
    level = user[1]
    words_count = user[2]
    repetitions = user[3]
    
    # Безопасно получаем часовой пояс пользователя с проверкой на валидность
    user_tz = user[5] if len(user) > 5 and user[5] else "Europe/Moscow"
    try:
        # Проверяем валидность часового пояса
        ZoneInfo(user_tz)
        now_local = now_server.astimezone(ZoneInfo(user_tz))
    except Exception as e:
        # В случае ошибки используем значение по умолчанию
        logger.error(f"Неверный часовой пояс {user_tz} для пользователя {chat_id}: {e}")
        user_tz = "Europe/Moscow"
        try:
            now_local = now_server.astimezone(ZoneInfo(user_tz))
            # Обновляем часовой пояс пользователя на корректное значение
            crud.update_user_timezone(chat_id, user_tz)
        except Exception as e2:
            logger.critical(f"Критическая ошибка с часовым поясом: {e2}")
            now_local = now_server  # Используем серверное время как крайний случай
    
    now_local_str = now_local.strftime("%H:%M")
    local_today_str = now_local.strftime("%Y-%m-%d")
    
    # Вычисляем базовое локальное время начала и окончания периода
    try:
        local_base_obj = datetime.strptime(f"{local_today_str} {FIRST_TIME}", "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(user_tz))
        local_end_obj = local_base_obj + timedelta(hours=DURATION_HOURS)
        end_time_str = local_end_obj.strftime("%H:%M")
    except Exception as e:
        logger.error(f"Ошибка вычисления времен для пользователя {chat_id}: {e}")
        return
    
    # Получаем список слов дня (это также обновляет кэш, если необходимо)
    try:
        result = get_daily_words_for_user(chat_id, level, words_count, repetitions,
                                         first_time=FIRST_TIME, duration_hours=DURATION_HOURS)
        if result is None:
            return
        messages, times = result

        # Отправка обычных уведомлений по расписанию
        if now_local_str in times:
            notif_index = times.index(now_local_str)
            message_text = messages[notif_index] if notif_index < len(messages) else ""
            try:
                asyncio.run_coroutine_threadsafe(
                    bot.send_message(chat_id, f"📌 Слова дня:\n{message_text}"),
                    loop
                )
            except Exception as e:
                logger.error(f"Error sending notification to user {chat_id}: {e}")
        
        # Если текущее время равно концу периода (FIRST_TIME + DURATION_HOURS)
        if now_local_str == end_time_str:
            # Проверяем, было ли уже отправлено уведомление для данного пользователя сегодня
            if quiz_reminder_sent.get(chat_id) != local_today_str:
                try:
                    asyncio.run_coroutine_threadsafe(
                        bot.send_message(chat_id, "Пройдите квиз чтобы слова добавились в Мой словарь"),
                        loop
                    )
                    quiz_reminder_sent[chat_id] = local_today_str
                except Exception as e:
                    logger.error(f"Error sending quiz reminder to user {chat_id}: {e}")

        # При наступлении DAILY_RESET_TIME сбрасываем кэш и сохраняем текущий список уникальных слов
        if now_local.strftime("%H:%M") == DAILY_RESET_TIME:
            try:
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
            except Exception as e:
                logger.error(f"Error processing daily reset for user {chat_id}: {e}")
    except Exception as e:
        logger.error(f"Error processing daily words for user {chat_id}: {e}")

        
def start_scheduler(bot: Bot, loop: asyncio.AbstractEventLoop):
    """
    Запускает APScheduler, который каждые 60 секунд вызывает scheduler_job.
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(scheduler_job, 'interval', minutes=1, args=[bot, loop])
    # Добавляем задачу для регулярной очистки кэша (каждые 6 часов)
    scheduler.add_job(lambda: daily_words_manager.clean_expired(), 'interval', hours=6)
    scheduler.add_job(lambda: previous_daily_words_manager.clean_expired(), 'interval', hours=6)
    scheduler.start()
    return scheduler