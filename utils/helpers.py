#pathtofile/utils/helpers.py
import os
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from config import LEVELS_DIR, REMINDER_START, DURATION_HOURS
from database import crud

# Кэш для ежедневных слов: ключ – chat_id, значение – (дата, messages, times, first_time, duration_hours, words_count, repetitions, tz)
daily_words_cache = {}
# Постоянное хранилище для зафиксированных наборов за сегодняшний день
daily_words_storage = {}

def load_words_for_level(level: str):
    filename = os.path.join(LEVELS_DIR, f"{level}.txt")
    if not os.path.exists(filename):
        return []
    with open(filename, encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]
    return words

def compute_notification_times(total_count, first_time, duration_hours, tz="Europe/Moscow"):
    """
    Вычисляет список из total_count времён уведомлений, начиная с first_time и равномерно распределяя
    интервал duration_hours между уведомлениями.
    Временные метки рассчитываются в часовом поясе, указанном в tz.
    Формат времени: "%H:%M".
    """
    base = datetime.strptime(first_time, "%H:%M").replace(tzinfo=ZoneInfo(tz))
    interval = timedelta(hours=duration_hours / total_count)
    times = [(base + n * interval).strftime("%H:%M") for n in range(total_count)]
    print(f"[DEBUG] compute_notification_times: total_count={total_count}, first_time={first_time}, duration_hours={duration_hours}, tz={tz}")
    print(f"[DEBUG] Computed times: {times}")
    return times

def get_daily_words_for_user(chat_id, level, words_count, repetitions, first_time, duration_hours):
    """
    Если для данного chat_id уже сохранён окончательный набор слов на сегодняшний день
    (в daily_words_storage) с теми же параметрами, возвращает его.
    Иначе, если в кэше уже есть сгенерированный набор за сегодня с такими же параметрами,
    возвращает его. Если параметры не совпадают, удаляет старую запись и генерирует новый набор.
    
    Генерирует новый набор слов (исключая уже выученные), повторяет его repetitions раз,
    вычисляет времена уведомлений для общего числа уведомлений (words_count * repetitions)
    с учетом часового пояса и сохраняет результат в кэш.
    
    Возвращает кортеж (repeated_messages, times) или None, если слов нет.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Сначала проверяем постоянное хранилище
    if chat_id in daily_words_storage:
        stored_entry = daily_words_storage[chat_id]
        if len(stored_entry) == 8:
            stored_date, messages, times, stored_first_time, stored_duration, stored_count, stored_reps, stored_tz = stored_entry
            if (stored_date == today and stored_first_time == first_time and 
                stored_duration == duration_hours and stored_count == words_count and stored_reps == repetitions):
                return messages, times

    # Проверяем кэш
    if chat_id in daily_words_cache:
        cached_entry = daily_words_cache[chat_id]
        if len(cached_entry) != 8:
            del daily_words_cache[chat_id]
        else:
            cached_date, messages, times, cached_first_time, cached_duration, cached_count, cached_reps, cached_tz = cached_entry
            if (cached_date == today and cached_first_time == first_time and 
                cached_duration == duration_hours and cached_count == words_count and cached_reps == repetitions):
                return messages, times
            else:
                del daily_words_cache[chat_id]

    words = load_words_for_level(level)
    if not words:
        return None

    learned = set(crud.get_learned_words(chat_id))
    available_words = [w for w in words if w not in learned]
    if not available_words:
        available_words = words

    if len(available_words) >= words_count:
        selected_words = random.sample(available_words, words_count)
    else:
        selected_words = random.choices(available_words, k=words_count)
    
    unique_messages = [f"🔹 {word}" for word in selected_words]
    repeated_messages = unique_messages * repetitions
    total_count = words_count * repetitions

    # Получаем часовой пояс пользователя
    user = crud.get_user(chat_id)
    user_tz = user[5] if user and len(user) > 5 and user[5] else "Europe/Moscow"
    
    times = compute_notification_times(total_count, first_time, duration_hours, tz=user_tz)
    
    daily_words_cache[chat_id] = (today, repeated_messages, times, first_time, duration_hours, words_count, repetitions, user_tz)
    return repeated_messages, times
