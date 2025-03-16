"""
Файл: utils/quiz_helpers.py
Описание: Функция для загрузки данных для квиза.
Ожидается, что для уровня существует файл (например, A1.txt) в папке levels,
где каждая строка имеет формат:
    word - translation
Возвращает список словарей: { "word": word, "translation": translation }
"""

import os
from config import LEVELS_DIR, DEFAULT_SETS

def load_quiz_data(level: str, chosen_set: str = None):
    """
    Загружает данные для квиза для указанного уровня.
    Если chosen_set не указан, используется основной сет из DEFAULT_SETS.
    Формат файла: каждая строка имеет формат "word - translation".
    """
    # Если выбранный сет не указан, берем основной по умолчанию для уровня
    if chosen_set is None:
        chosen_set = DEFAULT_SETS.get(level)
    # Формируем имя файла с учетом выбранного сета: например, "A1/Essential Everyday Words.txt"
    filename = os.path.join(LEVELS_DIR, level, f"{chosen_set}.txt")
    if not os.path.exists(filename):
        return []
    quiz_items = []
    with open(filename, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if " - " in line:
                parts = line.split(" - ", 1)
                word = parts[0].strip()
                translation = parts[1].strip()
                quiz_items.append({"word": word, "translation": translation})
    return quiz_items
