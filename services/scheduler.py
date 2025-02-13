#scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import asyncio
from math import ceil
from database import crud
from utils.helpers import load_words_for_level
from aiogram import Bot

# Параметры уведомлений
FIRST_TIME = "02:19"      # FT: время первого уведомления
DURATION_HOURS = 1        # DT: длительность периода уведомлений

def compute_notification_times(Y):
    """
    Вычисляет список из Y времён уведомлений.
    По формуле: Tₙ = FT + (n-1) · (DT / Y)
    Возвращает список строк в формате "HH:MM".
    """
    base = datetime.strptime(FIRST_TIME, "%H:%M")
    interval = timedelta(hours=DURATION_HOURS / Y)
    times = []
    for n in range(Y):
        t = base + n * interval
        formatted_time = t.strftime("%H:%M")
        times.append(formatted_time)
    # Логирование вычисленных времен
    print("Вычисленные времена уведомлений:", times)
    return times

def distribute_word_messages_cyclic(words_list, Y):
    """
    Принимает список слов words_list длиной T = 3*X (каждое слово повторено 3 раза)
    и вычисляет N = ceil(T / Y) – число слов в каждом уведомлении.
    Для уведомления с индексом i (0-based) выбирает слова:
         words_list[(i*N + j) mod T],  j = 0..N-1.
    Возвращает список из Y строк, где каждая строка – сообщение для уведомления.
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
    Для пользователя (user – кортеж: chat_id, level, words_per_day, notifications, reminder_time)
    загружает первые X слов для его уровня, повторяет их 3 раза и распределяет циклически по Y уведомлениям.
    Возвращает кортеж (messages, times), где:
      - messages: список из Y сообщений,
      - times: список времен уведомлений (Y значений).
    """
    _, level, words_per_day, notifications, _ = user
    X = words_per_day
    Y = notifications
    words = load_words_for_level(level)
    if not words:
        return None
    selected_words = words[:X]
    # Повторяем список 3 раза
    words_repeated = selected_words * 3
    messages = distribute_word_messages_cyclic(words_repeated, Y)
    times = compute_notification_times(Y)
    return messages, times

def scheduler_job(bot: Bot):
    now_str = datetime.now().strftime("%H:%M")
    base_obj = datetime.strptime(FIRST_TIME, "%H:%M")
    end_obj = base_obj + timedelta(hours=DURATION_HOURS)
    now_obj = datetime.strptime(now_str, "%H:%M")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Запуск scheduler_job")
    print(f"Текущее время: {now_str}, период отправки: {base_obj.strftime('%H:%M')} - {end_obj.strftime('%H:%M')}")

    if base_obj <= now_obj <= end_obj:
        users = crud.get_all_users()  # Получаем всех пользователей
        for user in users:
            result = compute_notification_message_for_user(user)
            if result is None:
                continue
            messages, times = result
            print(f"Пользователь {user[0]} | Вычисленные времена уведомлений: {times}")
            if now_str in times:
                notif_index = times.index(now_str)
                message_text = messages[notif_index] if notif_index < len(messages) else ""
                chat_id = user[0]
                print(f"Отправка уведомления пользователю {chat_id} в {now_str}: {message_text}")
                asyncio.create_task(bot.send_message(chat_id, f"📌 Слова дня:\n{message_text}"))
    else:
        print(f"Текущее время {now_str} не входит в интервал уведомлений.")

    if now_str == end_obj.strftime("%H:%M"):
        # Здесь можно добавить логику завершения дня (например, запуск викторины)
        pass

def start_scheduler(bot: Bot):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(scheduler_job, 'interval', minutes=1, args=[bot])
    scheduler.start()
    return scheduler

