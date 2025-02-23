# keyboards/submenus.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def words_day_keyboard():
    # В сообщении «Слова дня» достаточно иметь кнопку «Назад»
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("Назад", callback_data="menu:back"))
    return keyboard

def learning_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📚 Тест (множественный выбор)", callback_data="test_level:start"),
        InlineKeyboardButton("🎯 Викторина", callback_data="learning:quiz"),
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
