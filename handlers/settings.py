#pathtofile/handlers/settings.py
from aiogram import types, Dispatcher, Bot
from aiogram.dispatcher.filters import Command
from keyboards.submenus import settings_menu_keyboard
from keyboards.main_menu import main_menu_keyboard
from database import crud
from functools import partial
from utils.helpers import daily_words_cache

# Глобальный словарь для ожидания ввода настроек от пользователя.
# Ключ: chat_id, значение: "words" или "repetitions"
pending_settings = {}

async def show_settings_callback(callback: types.CallbackQuery, bot: Bot):
    """
    Показывает меню настроек.
    """
    chat_id = callback.from_user.id
    await bot.send_message(chat_id, "Настройки бота:", reply_markup=settings_menu_keyboard())
    await callback.answer()

async def process_settings_choice_callback(callback: types.CallbackQuery, bot: Bot):
    """
    Обрабатывает выбор настройки (количество слов, количество повторений, выбор уровня, мои настройки).
    """
    chat_id = callback.from_user.id
    try:
        _, option = callback.data.split(":", 1)
    except ValueError:
        await callback.answer("Неверный формат данных.", show_alert=True)
        return

    if option == "level":
        levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
        keyboard = types.InlineKeyboardMarkup(row_width=3)
        for lvl in levels:
            keyboard.add(types.InlineKeyboardButton(lvl, callback_data=f"set_level:{lvl}"))
        await bot.send_message(chat_id, "Выберите уровень:", reply_markup=keyboard)
    elif option == "words":
        pending_settings[chat_id] = "words"
        await bot.send_message(chat_id, "Введите количество слов в день (от 1 до 20):")
    elif option == "repetitions":
        pending_settings[chat_id] = "repetitions"
        await bot.send_message(chat_id, "Введите количество повторений (от 1 до 5):")
    elif option == "mysettings":
        user = crud.get_user(chat_id)
        if not user:
            await bot.send_message(chat_id, "Профиль не найден. Пожалуйста, используйте /start.")
        else:
            level = user[1]
            words_count = user[2]
            repetitions = user[3]
            text = (f"Ваш уровень: {level}\n"
                    f"Количество слов в день: {words_count}\n"
                    f"Количество повторений в день: {repetitions}")
            await bot.send_message(chat_id, text, reply_markup=settings_menu_keyboard())
    await callback.answer()

async def process_set_level_callback(callback: types.CallbackQuery, bot: Bot):
    """
    Обрабатывает выбор уровня (A1, A2, B1 и т.д.). После выбора уровня очищает кэш и возвращает меню настроек.
    """
    chat_id = callback.from_user.id
    try:
        _, level = callback.data.split(":", 1)
    except ValueError:
        await callback.answer("Неверный формат данных.", show_alert=True)
        return

    crud.update_user_level(chat_id, level)
    if chat_id in daily_words_cache:
        del daily_words_cache[chat_id]
    await bot.send_message(chat_id, f"Уровень установлен на {level}.", reply_markup=settings_menu_keyboard())
    await callback.answer()

async def process_text_setting(message: types.Message):
    """
    Обрабатывает текстовый ввод для настроек (количество слов, количество повторений).
    Если пользователь вводит неверное значение, выводится ошибка и меню настроек.
    Если значение корректное – обновляется БД, кэш очищается и отправляется сообщение об успехе + меню настроек.
    """
    chat_id = message.chat.id
    if chat_id not in pending_settings:
        return

    setting_type = pending_settings.pop(chat_id)
    text = message.text.strip()

    if not text.isdigit():
        await message.answer("Ошибка: введите корректное число.", reply_markup=settings_menu_keyboard())
        return

    value = int(text)
    if setting_type == "words":
        if not (1 <= value <= 20):
            await message.answer("Ошибка: число должно быть от 1 до 20.", reply_markup=settings_menu_keyboard())
            return
        crud.update_user_words_per_day(chat_id, value)
        if chat_id in daily_words_cache:
            del daily_words_cache[chat_id]
        await message.answer(f"Количество слов в день установлено на {value}.", reply_markup=settings_menu_keyboard())
    elif setting_type == "repetitions":
        if not (1 <= value <= 5):
            await message.answer("Ошибка: число должно быть от 1 до 5.", reply_markup=settings_menu_keyboard())
            return
        crud.update_user_notifications(chat_id, value)
        if chat_id in daily_words_cache:
            del daily_words_cache[chat_id]
        await message.answer(f"Количество повторений установлено на {value}.", reply_markup=settings_menu_keyboard())

def register_settings_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(
        partial(show_settings_callback, bot=bot),
        lambda c: c.data == "menu:settings"
    )
    dp.register_callback_query_handler(
        partial(process_settings_choice_callback, bot=bot),
        lambda c: c.data and c.data.startswith("settings:")
    )
    dp.register_callback_query_handler(
        partial(process_set_level_callback, bot=bot),
        lambda c: c.data and c.data.startswith("set_level:")
    )
    dp.register_message_handler(process_text_setting, content_types=['text'])
