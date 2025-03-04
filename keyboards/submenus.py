#pathtofile/keyboards/submenus.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📌 Слова дня", callback_data="menu:words_day"),
        InlineKeyboardButton("📖 Обучение", callback_data="menu:learning")
    )
    keyboard.add(
        InlineKeyboardButton("📚 Мой словарь", callback_data="menu:dictionary"),
        InlineKeyboardButton("⚙️ Настройки", callback_data="menu:settings")
    )
    keyboard.add(
        InlineKeyboardButton("🎯 Квиз", callback_data="quiz:start"),
        InlineKeyboardButton("❓ Помощь", callback_data="menu:help")
    )
    return keyboard

def words_day_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("Назад", callback_data="menu:back"))
    return keyboard

def learning_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📚 Тест (множественный выбор)", callback_data="test_level:start"),
        InlineKeyboardButton("🎯 Викторина", callback_data="learning:quiz")
    )
    keyboard.add(
        InlineKeyboardButton("📝 Заучивание", callback_data="learning:memorize"),
        InlineKeyboardButton("🔙 Назад", callback_data="menu:back")
    )
    return keyboard

def dictionary_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📈 +10 слов", callback_data="dictionary:+10"),
        InlineKeyboardButton("📊 +50 слов", callback_data="dictionary:+50")
    )
    keyboard.add(
        InlineKeyboardButton("📖 Показать все", callback_data="dictionary:all"),
        InlineKeyboardButton("🔙 Назад", callback_data="menu:back")
    )
    return keyboard

def settings_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("Выбор уровня", callback_data="settings:level"),
        InlineKeyboardButton("Количество слов", callback_data="settings:words"),
        InlineKeyboardButton("Количество повторений", callback_data="settings:repetitions"),
        InlineKeyboardButton("Выбор часового пояса", callback_data="settings:timezone"),
        InlineKeyboardButton("Мои настройки", callback_data="settings:mysettings"),
        InlineKeyboardButton("Назад", callback_data="menu:back")
    )
    return keyboard

def help_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("ℹ️ О боте", callback_data="help:about"),
        InlineKeyboardButton("📜 Список команд", callback_data="help:commands"),
        InlineKeyboardButton("✉️ Обратная связь", callback_data="help:feedback"),
        InlineKeyboardButton("Назад", callback_data="menu:back")
    )
    return keyboard

def quiz_keyboard(options, question_index):
    """
    Создает клавиатуру для квиза.
    Каждая кнопка для вариантов ответа имеет callback_data в формате "quiz:answer:<question_index>:<option_index>".
    Дополнительно добавляются кнопки "Назад" и "Остановить квиз".
    Клавиатура оформлена в два столбца.
    """
    keyboard = InlineKeyboardMarkup(row_width=2)
    for i, option in enumerate(options):
        keyboard.add(InlineKeyboardButton(option, callback_data=f"quiz:answer:{question_index}:{i}"))
    keyboard.add(
        InlineKeyboardButton("Назад", callback_data="quiz:back"),
        InlineKeyboardButton("Остановить квиз", callback_data="quiz:stop")
    )
    return keyboard
