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

def load_quiz_data_for_set(level: str, selected_set: str):
    """
    Загружает данные для квиза из файла уровня/сета,
    т.е. из файла: levels/<level>/<selected_set>.txt
    """
    filename = os.path.join("levels", level, f"{selected_set}.txt")
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
