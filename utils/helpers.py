# utils/helpers.py
import os
import random
from config import LEVELS_DIR

def load_words_for_level(level: str):
    filename = os.path.join(LEVELS_DIR, f"{level}.txt")
    if not os.path.exists(filename):
        return []
    with open(filename, encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]
    return words

def aggregate_daily_words(words, notifications, words_per_day):
    """
    Если, например, words_per_day=5 и notifications=10, то каждое слово повторяется 2 раза.
    Если notifications меньше, можно сгруппировать несколько слов в одном сообщении.
    Эта функция возвращает список сообщений для рассылки.
    """
    messages = []
    if notifications >= words_per_day:
        repeat = notifications // words_per_day
        for word in words:
            for _ in range(repeat):
                messages.append(word)
    else:
        # Если уведомлений меньше, группируем несколько слов в одном сообщении.
        group_size = words_per_day // notifications
        for i in range(notifications):
            group = words[i*group_size:(i+1)*group_size]
            messages.append(", ".join(group))
    return messages
