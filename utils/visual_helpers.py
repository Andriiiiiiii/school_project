# utils/visual_helpers.py
import logging
from typing import List, Tuple
import re

logger = logging.getLogger(__name__)

# Символы для визуального оформления
PROGRESS_FILLED = "█"
PROGRESS_EMPTY = "░"
BULLET_STYLES = {
    "standard": "• ",
    "numbered": None,  # Будет отформатировано как "1. ", "2. " и т.д.
    "arrow": "→ ",
    "star": "★ ",
    "check": "✓ ",
    "diamond": "◆ "
}

SECTION_DIVIDERS = {
    "light": "─",
    "medium": "━",
    "heavy": "═",
    "double": "═",
    "decorated": "•─•",
    "star": "✧･ﾟ: *✧･ﾟ:* *:･ﾟ✧*:･ﾟ✧"
}

# Эмодзи по категориям для визуального оформления
EMOJI = {
    "learn": ["📚", "📖", "📝", "🔍", "🎓", "✏️", "📘"],
    "success": ["✅", "🎉", "🏆", "🌟", "👍", "🎊", "💯"],
    "warning": ["⚠️", "❗", "🔔", "📢", "‼️"],
    "error": ["❌", "🚫", "⛔", "🔴", "❗"],
    "time": ["⏰", "⌚", "🕒", "⏱️", "📅"],
    "level": ["🔄", "🔼", "🆙", "📊", "📈"],
    "quiz": ["🎯", "❓", "🎮", "🧩", "🎲", "🎪"],
    "settings": ["⚙️", "🔧", "🛠️", "🔨", "🔩"],
    "menu": ["📋", "📊", "📑", "📁"]
}

# Стикеры для поздравлений (ID стикеров)
CONGRATULATION_STICKERS = [
    "CAACAgIAAxkBAAEKX2RlB3TN7AAB3o7Dh4QXsaU6SWHccpQAAjcHAAJlhUhLOh2LB8jQBDswBA",  # Пример ID стикера
    "CAACAgIAAxkBAAEKX2ZlB3VnXKiJ7AABaRpSmMhlg3JFQmQAAkIHAAL2U-hLNLtFY_Tf0GUwBA",  # Пример ID стикера
    "CAACAgIAAxkBAAEKX2hlB3V8Tit78f3MF-Z20VkfUvl7KAACbgUAAvLm-UtcQxCPuiDzijAE"    # Пример ID стикера
]

def format_header(text: str, emoji: str = None, top_divider: str = None, bottom_divider: str = None) -> str:
    """Форматирует заголовок с опциональными эмодзи и разделителями."""
    header = f"{emoji} {text} {emoji}" if emoji else text
    
    if top_divider:
        header = f"{top_divider}\n{header}"
    if bottom_divider:
        header = f"{header}\n{bottom_divider}"
        
    return header

def format_bullet_list(items: List[str], style: str = "standard", start_index: int = 1) -> str:
    """Форматирует список элементов с различными стилями маркеров."""
    bullet_style = BULLET_STYLES.get(style, BULLET_STYLES["standard"])
    formatted_items = []
    
    for i, item in enumerate(items):
        if style == "numbered":
            line = f"{i+start_index}. {item}"
        else:
            line = f"{bullet_style}{item}"
        formatted_items.append(line)
        
    return "\n".join(formatted_items)

def format_word_item(word: str, translation: str, transcription: str = None, 
                    example: str = None, emoji: str = None) -> str:
    """Форматирует словарное слово с деталями."""
    if not emoji:
        emoji = "📝"
        
    result = f"{emoji} *{word}* — _{translation}_"
    
    if transcription:
        result += f"\n  [{transcription}]"
        
    if example:
        result += f"\n  Пример: \"{example}\""
        
    return result

# Добавить функцию format_progress_bar, если её ещё нет:

def format_progress_bar(current: int, total: int, length: int = 10) -> str:
    """Создает текстовую шкалу прогресса."""
    filled_length = int(length * current / total) if total > 0 else 0
    filled = "█" * filled_length
    empty = "░" * (length - filled_length)
    bar = filled + empty
    return f"[{bar}] {current}/{total}"

def format_quiz_question(question_number: int, total_questions: int, word: str, 
                         options: List[str], is_revision: bool = False) -> str:
    """Форматирует вопрос квиза с индикатором прогресса."""
    progress = format_progress_bar(question_number, total_questions)
    
    # Дополнительная проверка - удаляем возможный перевод из слова
    clean_word = word
    if " - " in clean_word:
        clean_word = clean_word.split(" - ", 1)[0].strip()
    elif " – " in clean_word:
        clean_word = clean_word.split(" – ", 1)[0].strip()
    elif ": " in clean_word:
        clean_word = clean_word.split(": ", 1)[0].strip()
    
    header = "🔄 ПОВТОРЕНИЕ" if is_revision else "🎯 СЛОВАРНЫЙ КВИЗ"
    question = f"{header}\n{progress}\n\nВопрос {question_number}/{total_questions}:\n\nКакой перевод слова '*{clean_word}*'?"
    
    return question

def format_result_message(correct: int, total: int, is_revision: bool = False) -> str:
    """Форматирует сообщение с результатами квиза."""
    percentage = (correct / total) * 100 if total > 0 else 0
    
    # Выбираем эмодзи на основе результата
    if percentage >= 90:
        emoji = "🎉"
    elif percentage >= 70:
        emoji = "👍"
    elif percentage >= 50:
        emoji = "👌"
    else:
        emoji = "🔄"
        
    progress = format_progress_bar(correct, total, 20)
    
    header = f"{emoji} Квиз завершен! {emoji}"
    divider = SECTION_DIVIDERS["decorated"]
    
    message = f"{header}\n{divider}\n\n"
    message += f"*Счет:* {correct} из {total} ({percentage:.1f}%)\n{progress}\n\n"
    
    if is_revision:
        message += "Вы были в *режиме повторения*. Эти слова уже в вашем словаре.\n\n"
        if percentage < 70:
            message += "💡 *Совет:* Рассмотрите возможность повторного изучения этих слов для улучшения запоминания."
    else:
        message += "Правильные ответы добавлены в ваш словарь.\n\n"
        if percentage < 70:
            message += "💡 *Совет:* Попробуйте квиз снова завтра, чтобы освоить слова, которые вы пропустили."
            
    return message

def extract_english(word_line: str) -> str:
    """Извлекает английскую часть из строки формата 'word - translation'."""
    try:
        if not word_line or not isinstance(word_line, str):
            return ""
            
        # Удаляем ведущие эмодзи или символы
        cleaned_line = re.sub(r'^[^\w]*', '', word_line).strip()
            
        # Проверяем различные форматы разделителей
        for separator in [" - ", " – ", ": "]:
            if separator in cleaned_line:
                return cleaned_line.split(separator, 1)[0].strip()
                
        return cleaned_line
    except Exception as e:
        logger.error(f"Ошибка при извлечении английского слова из '{word_line}': {e}")
        return word_line.strip() if isinstance(word_line, str) else ""

def format_daily_words_message(messages: List[str], times: List[str], chosen_set: str = None, total_words: int = None) -> str:
    """
    Форматирует сообщение со словами дня с улучшенным визуальным представлением.
    
    Args:
        messages: Список сообщений со словами
        times: Список времен отправки
        chosen_set: Название выбранного набора слов (опционально)
        total_words: Общее количество слов в наборе (опционально)
    """
    header = "📚 Словарь на сегодня"
    
    # Добавляем информацию о наборе слов, если она доступна
    if chosen_set:
        if total_words:
            header += f"\nИз набора: *«{chosen_set}»* (~{total_words} слов)"
        else:
            header += f"\nИз набора: *«{chosen_set}»*"
    
    result = f"{header}\n\n"
    
    # Извлекаем любое префиксное сообщение (начинающееся с 🎓 или ⚠️)
    prefix_message = ""
    word_messages = messages.copy()
    
    if messages and (messages[0].startswith("🎓") or messages[0].startswith("⚠️")):
        prefix_message = messages[0]
        word_messages = messages[1:]
    
    if prefix_message:
        result += f"{prefix_message}\n\n"
    
    # Группируем слова по времени уведомления
    time_groups = {}
    for i, time in enumerate(times):
        if i < len(word_messages):
            if time not in time_groups:
                time_groups[time] = []
            time_groups[time].append(word_messages[i])
    
    # Форматируем каждую временную группу
    for time, words in time_groups.items():
        result += f"⏰ *{time}*\n"
        for word in words:
            # Удаляем префикс эмодзи, если он есть, и добавляем наше стандартное форматирование
            word_text = word
            if word.startswith("🔹 "):
                word_text = word[2:].strip()
            result += f"• {word_text}\n"
        result += "\n"
    
    return result

def format_dictionary_message(words: List[Tuple[str, str]]) -> str:
    
    """Форматирует записи словаря с улучшенным визуальным представлением."""
    if not words:
        return "📚 *Ваш словарь пуст*\n\nПройдите квизы, чтобы добавить слова в свой словарь!"
    
    header = "📚 Ваш словарь"
    
    result = f"{header}\n\n"
    
    # Группируем слова по алфавиту
    alpha_dict = {}
    for word, translation in words:
        first_letter = word[0].upper() if word else "?"
        if first_letter not in alpha_dict:
            alpha_dict[first_letter] = []
        alpha_dict[first_letter].append((word, translation))
    
    # Сортируем ключи по алфавиту
    for letter in sorted(alpha_dict.keys()):
        result += f"*{letter}*\n"
        for word, translation in alpha_dict[letter]:
            result += f"• {word} — _{translation}_\n"
        result += "\n"
    
    return result

def format_level_test_question(q_index: int, total: int, level: str, word: str) -> str:
    """Форматирует вопрос теста уровня с визуальными улучшениями."""
    progress = format_progress_bar(q_index + 1, total)
    
    header = f"📊 Тест уровня: {level}"
    
    result = f"{header}\n\n"
    result += f"{progress}\n\n"
    result += f"Вопрос {q_index + 1} из {total}:\n\n"
    result += f"Какой перевод слова '*{word}*'?"
    
    return result

def format_level_test_results(results_by_level: dict, new_level: str) -> str:
    """Форматирует результаты теста уровня с визуальными улучшениями."""
    header = "📊 Результаты теста уровня"
    
    result = f"{header}\n\n"
    
    # Добавляем результаты по уровням
    result += "*Результаты по уровням*\n"
    for level, (score, total) in sorted(results_by_level.items()):
        progress = format_progress_bar(score, total, 10)
        result += f"*{level}*: {score}/{total} {progress}\n"
    
    result += f"\n"
    result += f"🎓 *Ваш уровень теперь: {new_level}*\n\n"
    
    if new_level == "A1":
        result += "Продолжайте обучение! Вы только начинаете."
    elif new_level in ["A2", "B1"]:
        result += "Отличный прогресс! Вы строите прочный фундамент."
    elif new_level in ["B2", "C1"]:
        result += "Превосходно! Вы становитесь довольно продвинутым."
    else:  # C2
        result += "Великолепно! Вы достигли наивысшего уровня."
    
    return result

def format_settings_overview(user_settings: dict) -> str:
    """Форматирует настройки пользователя с визуальными улучшениями."""
    header = "⚙️ Ваши настройки"
    
    result = f"{header}\n\n"
    
    # Форматируем каждую настройку с подходящим эмодзи
    result += f"🔤 *Уровень*: {user_settings.get('level', 'Не установлен')}\n"
    result += f"📝 *Слов в день*: {user_settings.get('words_per_day', 'Не установлено')}\n"
    result += f"🔁 *Повторений*: {user_settings.get('repetitions', 'Не установлено')}\n"
    result += f"🌐 *Часовой пояс*: {user_settings.get('timezone', 'Не установлен')}\n"
    result += f"📚 *Выбранный набор*: {user_settings.get('chosen_set', 'Не выбран')}\n"
    
    return result

def format_result_message(correct: int, total: int, is_revision: bool = False) -> str:
    """Форматирует сообщение с результатами квиза."""
    percentage = (correct / total) * 100 if total > 0 else 0
    
    # Выбираем эмодзи на основе результата
    if percentage >= 90:
        emoji = "🎉"
    elif percentage >= 70:
        emoji = "👍"
    elif percentage >= 50:
        emoji = "👌"
    else:
        emoji = "🔄"
        
    progress = format_progress_bar(correct, total, 20)
    
    header = f"{emoji} Квиз завершен! {emoji}"
    
    message = f"{header}\n\n"
    message += f"*Счет:* {correct} из {total} ({percentage:.1f}%)\n{progress}\n\n"
    
    if is_revision:
        message += "Вы были в *режиме повторения*. Эти слова уже в вашем словаре.\n\n"
        if percentage < 70:
            message += "💡 *Совет:* Рассмотрите возможность повторного изучения этих слов для улучшения запоминания."
    else:
        message += "Правильные ответы добавлены в ваш словарь.\n\n"
        if percentage < 70:
            message += "💡 *Совет:* Попробуйте квиз снова завтра, чтобы освоить слова, которые вы пропустили."
            
    return message

def truncate_daily_words_message(formatted_message: str, unique_words: List[str], 
                                 words_count: int, repetitions: int,
                                 chosen_set: str = None, total_words: int = None) -> str:
    """
    Обрезает сообщение со словами дня, если оно слишком длинное для Telegram.
    
    Args:
        formatted_message: Полное отформатированное сообщение
        unique_words: Список уникальных слов на сегодня
        words_count: Количество слов в день
        repetitions: Количество повторений
        chosen_set: Название набора слов
        total_words: Общее количество слов в наборе
        
    Returns:
        Обрезанное сообщение, если необходимо, или оригинальное
    """
    # Telegram имеет лимит в 4096 символов
    if len(formatted_message) <= 4000:  # Оставляем запас
        return formatted_message
    
    # Создаем заголовок
    header = "📚 Словарь на сегодня"
    if chosen_set:
        header += f"\nИз набора: *«{chosen_set}»*"
        if total_words:
            header += f" (~{total_words} слов)"
    header += "\n\n"
    
    # Определяем, есть ли специальный префикс (режим повторения или предупреждение)
    prefix_msg = ""
    clean_words = unique_words
    if unique_words and (unique_words[0].startswith("🎓") or unique_words[0].startswith("⚠️")):
        prefix_msg = unique_words[0] + "\n\n"
        clean_words = unique_words[1:]
    
    # Очищаем слова от символов
    words_list = []
    for word in clean_words:
        clean_word = word.replace("🔹 ", "").strip()
        if clean_word and not (clean_word.startswith("🎓") or clean_word.startswith("⚠️")):
            words_list.append(f"• {clean_word}")
    
    # Определяем максимальное количество слов для показа
    max_words = 15
    show_words = words_list[:max_words]
    
    # Формируем сокращенное сообщение
    shortened_message = header + prefix_msg
    
    if len(words_list) > max_words:
        shortened_message += f"*Первые {max_words} из {len(words_list)} слов на сегодня:*\n\n"
        shortened_message += "\n".join(show_words)
        shortened_message += f"\n\n...и еще {len(words_list) - max_words} слов"
    else:
        shortened_message += f"*Сегодняшние слова ({len(words_list)} уникальных):*\n\n"
        shortened_message += "\n".join(show_words)
    
    # Добавляем примечание о расписании
    shortened_message += (
        f"\n\n⚠️ *Примечание:* Из-за большого количества повторений ({repetitions}×) "
        f"полное расписание не может быть показано. "
        f"Все слова будут приходить в уведомлениях в течение дня."
    )
    
    return shortened_message