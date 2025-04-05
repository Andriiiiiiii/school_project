from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import random

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

def dictionary_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    # Add Clear Dictionary button
    keyboard.add(InlineKeyboardButton("🗑 Очистить словарь", callback_data="dictionary:clear_confirm"))
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="menu:back"))
    return keyboard

# New confirmation keyboard for dictionary clearing
def clear_dictionary_confirm_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Да, очистить", callback_data="dictionary:clear_confirmed"),
        InlineKeyboardButton("❌ Нет, отмена", callback_data="dictionary:clear_cancel")
    )
    return keyboard

def set_change_confirm_keyboard(encoded_set_name):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Да, сменить", callback_data=f"set_change_confirmed:{encoded_set_name}"),
        InlineKeyboardButton("❌ Нет, отмена", callback_data="set_change_cancel")
    )
    return keyboard

def settings_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("Выбор уровня", callback_data="settings:level"),
        InlineKeyboardButton("Настройки уведомлений", callback_data="settings:notifications"),
        InlineKeyboardButton("Выбор сета", callback_data="settings:set"),
        InlineKeyboardButton("Мои настройки", callback_data="settings:mysettings"),
        InlineKeyboardButton("Назад", callback_data="menu:back")
    )
    return keyboard

def notification_settings_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("Количество слов", callback_data="settings:words"),
        InlineKeyboardButton("Количество повторений", callback_data="settings:repetitions"),
        InlineKeyboardButton("Выбор часового пояса", callback_data="settings:timezone"),
        InlineKeyboardButton("Назад", callback_data="settings:back")
    )
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
