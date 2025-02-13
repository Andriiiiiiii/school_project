
#words.py
import os
from math import ceil
from datetime import datetime, timedelta
from aiogram import types, Dispatcher, Bot
from database import crud
from utils.helpers import load_words_for_level  # Функция, которая загружает слова для уровня из файлов levels/<level>.txt
from keyboards.submenus import words_day_keyboard

# Параметры уведомлений (FT и DT)
FIRST_TIME = "02:19"      # Время первого уведомления (FT)
DURATION_HOURS = 1       # Длительность периода уведомлений (DT) – от FT до FT+DT (например, 10:00–22:00)

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
        times.append(t.strftime("%H:%M"))
    return times

def distribute_word_messages_cyclic(words_list, Y):
    """
    Принимает список слов words_list длиной T = 3*X (каждое слово повторено 3 раза).
    Вычисляет N = ceil(T / Y) – число слов в каждом уведомлении.
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

async def send_words_day_schedule(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик кнопки "Слова дня".
    Получает настройки пользователя: X (words_per_day) и Y (notifications),
    загружает первые X слов для его уровня, формирует список из 3*X слов,
    распределяет их циклически по Y уведомлениям (каждое уведомление содержит ceil(3X/Y) слов),
    вычисляет времена уведомлений по формуле Tₙ = FT + (n-1)*(DT/Y)
    и отправляет пользователю расписание уведомлений.
    """
    chat_id = callback.from_user.id
    user = crud.get_user(chat_id)
    if not user:
        await bot.send_message(chat_id, "Профиль не найден. Пожалуйста, используйте /start.")
        return

    # Извлекаем параметры: уровень, X и Y
    _, level, words_per_day, notifications, _ = user
    X = words_per_day
    Y = notifications

    # Загружаем слова для уровня (берем первые X слов)
    words = load_words_for_level(level)
    if not words:
        await bot.send_message(chat_id, f"⚠️ Нет слов для уровня {level}.")
        return
    selected_words = words[:X]

    # Формируем список из 3*X слов (каждое слово повторяется 3 раза)
    words_repeated = selected_words * 3

    # Распределяем слова циклически по Y уведомлениям
    messages = distribute_word_messages_cyclic(words_repeated, Y)
    times = compute_notification_times(Y)

    # Формируем итоговый текст расписания
    text = "📌 Сегодня вам будут отправлены следующие слова:\n\n"
    for i in range(Y):
        t = times[i]
        msg = messages[i] if messages[i] else "(нет слов)"
        text += f"⏰ {t}:\n{msg}\n\n"
    text += "Нажмите кнопку ниже для возврата в главное меню."

    await bot.send_message(chat_id, text, reply_markup=words_day_keyboard())
    await callback.answer()

def register_words_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(
        lambda c: send_words_day_schedule(c, bot),
        lambda c: c.data == "menu:words_day"
    )