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
    """Создает улучшенное двухколоночное меню настроек с эмодзи согласно требованиям."""
    keyboard = InlineKeyboardMarkup(row_width=2)  # Устанавливаем 2 столбца
    
    # Первый столбец: Уровень, Уведомления, Часовой пояс
    # Второй столбец: Мой профиль, Наборы слов, Назад
    keyboard.add(
        InlineKeyboardButton("🔤 Уровень", callback_data="settings:level"),
        InlineKeyboardButton("👤 Мой профиль", callback_data="settings:mysettings")
    )
    keyboard.add(
        InlineKeyboardButton("⏰ Уведомления", callback_data="settings:notifications"),
        InlineKeyboardButton("📚 Наборы слов", callback_data="settings:set")
    )
    keyboard.add(
        InlineKeyboardButton("🌐 Часовой пояс", callback_data="settings:timezone"),
        InlineKeyboardButton("🔙 Назад", callback_data="menu:back")
    )
    
    return keyboard   

def notification_settings_menu_keyboard():
    """Создает улучшенное меню настроек уведомлений с эмодзи."""
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    keyboard.add(
        InlineKeyboardButton("📊 Количество слов", callback_data="settings:words"),
        InlineKeyboardButton("🔄 Количество повторений", callback_data="settings:repetitions")
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Назад", callback_data="settings:back")
    )
    
    return keyboard

def learning_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📚 Тест по словарю", callback_data="learning:dictionary_test"),
        InlineKeyboardButton("📝 Заучивание сета", callback_data="learning:memorize_set")
    )
    keyboard.add(
        InlineKeyboardButton("⚙️ Настройки обучения", callback_data="learning:settings"),
        InlineKeyboardButton("🔙 Назад", callback_data="menu:back")
    )
    return keyboard

def learning_settings_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📊 Настройки теста", callback_data="learning:test_settings"),
        InlineKeyboardButton("📝 Настройки заучивания", callback_data="learning:memorize_settings")
    )
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="learning:back"))
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

def level_selection_keyboard():
    """Создает улучшенное меню выбора уровня с эмодзи."""
    keyboard = InlineKeyboardMarkup(row_width=3)  # Три уровня в ряд
    
    # Добавляем кнопки выбора уровня
    keyboard.add(
        InlineKeyboardButton("🟢 A1", callback_data="set_level:A1"),
        InlineKeyboardButton("🟢 A2", callback_data="set_level:A2"),
        InlineKeyboardButton("🟡 B1", callback_data="set_level:B1")
    )
    keyboard.add(
        InlineKeyboardButton("🟡 B2", callback_data="set_level:B2"),
        InlineKeyboardButton("🔴 C1", callback_data="set_level:C1"),
        InlineKeyboardButton("🔴 C2", callback_data="set_level:C2")
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Назад", callback_data="settings:back")
    )
    
    return keyboard