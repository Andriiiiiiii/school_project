from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import asyncio
from aiogram import Bot
from database import crud
from utils.helpers import get_daily_words_for_user, daily_words_cache, daily_words_storage
from config import REMINDER_START, DURATION_HOURS

# REMINDER_START и DURATION_HOURS берутся из конфига
FIRST_TIME = REMINDER_START

# saved_today больше не нужен, так как мы будем использовать daily_words_storage

def scheduler_job(bot: Bot, loop: asyncio.AbstractEventLoop):
    """
    Функция, вызываемая каждые 60 секунд планировщиком:
      - Для каждого пользователя вычисляется текущее время по серверу и формируется локальное время
        на основе REMINDER_START и DURATION_HOURS (здесь, для простоты, используется серверное время).
      - Если текущее время (до минут) находится в интервале уведомлений, отправляется уведомление.
      - Когда текущее время >= (REMINDER_START + DURATION_HOURS), если для пользователя набор не зафиксирован
        (нет записи в daily_words_storage), то уникальные слова из кэша сохраняются в базу (без дубликатов),
        и кэш переносится в daily_words_storage, чтобы новый набор не генерировался до 0:00.
    """
    now = datetime.now()
    now_str = now.strftime("%H:%M")
    today_str = now.strftime("%Y-%m-%d")
    base_obj = datetime.strptime(f"{today_str} {FIRST_TIME}", "%Y-%m-%d %H:%M")
    end_obj = base_obj + timedelta(hours=DURATION_HOURS)
    
    users = crud.get_all_users()
    for user in users:
        chat_id = user[0]
        # Используем настройки из базы: user[2] = words_per_day, user[3] = repetitions
        result = get_daily_words_for_user(chat_id, user[1], user[2], user[3],
                                           first_time=FIRST_TIME, duration_hours=DURATION_HOURS)
        if result is None:
            continue
        messages, times = result
        if now_str in times:
            notif_index = times.index(now_str)
            message_text = messages[notif_index] if notif_index < len(messages) else ""
            asyncio.run_coroutine_threadsafe(
                bot.send_message(chat_id, f"📌 Слова дня:\n{message_text}"),
                loop
            )
            break  # Отправляем уведомление только один раз за запуск

    # Если текущее время >= конца интервала, фиксируем набор (только один раз для каждого пользователя)
    if now >= end_obj:
        for user in users:
            chat_id = user[0]
            # Если уже зафиксирован набор для этого пользователя сегодня, пропускаем
            if chat_id in daily_words_storage and daily_words_storage[chat_id][0] == today_str:
                continue
            if chat_id in daily_words_cache:
                _, messages, _, _, _, _, _ = daily_words_cache[chat_id]
                unique_words = set(msg.replace("🔹 ", "") for msg in messages)
                for word in unique_words:
                    crud.add_learned_word(chat_id, word, today_str)
                # Переносим набор из кэша в постоянное хранилище, чтобы он не обновлялся до 0:00
                daily_words_storage[chat_id] = daily_words_cache[chat_id]
                # Не удаляем запись из daily_words_cache, чтобы get_daily_words_for_user сначала проверял daily_words_storage
        # Дополнительная логика для запуска теста может быть добавлена здесь

def start_scheduler(bot: Bot, loop: asyncio.AbstractEventLoop):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(scheduler_job, 'interval', minutes=1, args=[bot, loop])
    scheduler.start()
    return scheduler
