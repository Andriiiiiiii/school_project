from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import asyncio
from math import ceil
from database import crud
from utils.helpers import load_words_for_level
from aiogram import Bot

# Константы для уведомлений: с 10:00 до 20:00
FIRST_TIME = "10:00"        # Начало интервала уведомлений
DURATION_HOURS = 10         # Длительность интервала уведомлений

def compute_notification_times(Y):
    """
    Вычисляет список из Y времен уведомлений, начиная с FIRST_TIME и равномерно распределяя
    интервал DURATION_HOURS между уведомлениями.
    """
    base = datetime.strptime(FIRST_TIME, "%H:%M")
    interval = timedelta(hours=DURATION_HOURS / Y)
    times = [(base + n * interval).strftime("%H:%M") for n in range(Y)]
    return times

def distribute_word_messages_cyclic(words_list, Y):
    """
    Равномерно распределяет повторённые слова по Y уведомлениям.
    """
    T = len(words_list)
    N = ceil(T / Y)
    messages = []
    for i in range(Y):
        msg_words = [words_list[(i * N + j) % T] for j in range(N)]
        messages.append("\n".join(f"🔹 {word}" for word in msg_words))
    return messages

def compute_notification_message_for_user(user):
    """
    Для пользователя (настройки из БД) вычисляет сообщения уведомлений:
      - Берёт уровень, количество слов (X) и число уведомлений (Y),
      - Загружает первые X слов для уровня,
      - Повторяет их 3 раза,
      - Равномерно распределяет слова по Y уведомлениям,
      - Вычисляет времена уведомлений.
    Возвращает кортеж (messages, times) или None, если слов нет.
    """
    _, level, words_per_day, notifications, _ = user
    X = words_per_day
    Y = notifications
    words = load_words_for_level(level)
    if not words:
        return None
    selected_words = words[:X]
    words_repeated = selected_words * 3
    messages = distribute_word_messages_cyclic(words_repeated, Y)
    times = compute_notification_times(Y)
    return messages, times

def scheduler_job(bot: Bot, loop: asyncio.AbstractEventLoop):
    """
    Функция, вызываемая каждую минуту планировщиком:
      - Если текущее время входит в интервал уведомлений,
        для каждого пользователя вычисляются сообщения и времена уведомлений.
      - Если текущее время совпадает с рассчитанным, отправляется уведомление.
    """
    now_str = datetime.now().strftime("%H:%M")
    base_obj = datetime.strptime(FIRST_TIME, "%H:%M")
    end_obj = base_obj + timedelta(hours=DURATION_HOURS)
    now_obj = datetime.strptime(now_str, "%H:%M")

    if base_obj <= now_obj <= end_obj:
        users = crud.get_all_users()
        for user in users:
            result = compute_notification_message_for_user(user)
            if result is None:
                continue
            messages, times = result
            if now_str in times:
                notif_index = times.index(now_str)
                message_text = messages[notif_index] if notif_index < len(messages) else ""
                chat_id = user[0]
                asyncio.run_coroutine_threadsafe(
                    bot.send_message(chat_id, f"📌 Слова дня:\n{message_text}"),
                    loop
                )

    if now_str == end_obj.strftime("%H:%M"):
        # Здесь можно добавить логику завершения дня (например, запуск викторины)
        pass

def start_scheduler(bot: Bot, loop: asyncio.AbstractEventLoop):
    """
    Запускает планировщик APScheduler, который каждую минуту вызывает scheduler_job.
    Параметр loop – это основной event loop бота.
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(scheduler_job, 'interval', minutes=1, args=[bot, loop])
    scheduler.start()
    return scheduler
