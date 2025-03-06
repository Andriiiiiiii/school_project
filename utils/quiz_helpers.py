#utils/quiz_helpers.py
"""
Файл: utils/quiz_helpers.py
Описание: Функция для загрузки данных для квиза.
Ожидается, что для уровня существует файл (например, A1.txt) в папке levels,
где каждая строка имеет формат:
    word - translation
Возвращает список словарей: { "word": word, "translation": translation }
"""

import os

def load_quiz_data(level: str):
    filename = os.path.join("levels", f"{level}.txt")
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
