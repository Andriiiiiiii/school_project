# handlers/settings.py

from aiogram import types, Dispatcher, Bot
from keyboards.submenus import (
    notification_settings_menu_keyboard, 
    settings_menu_keyboard
)
from keyboards.main_menu import main_menu_keyboard
from database import crud
from functools import partial
from utils.helpers import daily_words_cache

# Глобальный словарь для хранения состояния ввода (какой параметр ожидается от пользователя)
pending_settings = {}

# Сопоставление смещения UTC с названием города/региона
timezones_map = {
    2: "Калининград",
    3: "Москва",
    4: "Самара",
    5: "Екатеринбург",
    6: "Омск",
    7: "Красноярск",
    8: "Иркутск",
    9: "Якутское",
    10: "Владивосток",
    11: "Магаданское",
    12: "Камчатское"
}


async def show_settings_callback(callback: types.CallbackQuery, bot: Bot):
    """
    Главное меню настроек.
    """
    chat_id = callback.from_user.id
    await bot.send_message(chat_id, "Настройки бота:", reply_markup=settings_menu_keyboard())
    await callback.answer()


async def process_settings_choice_callback(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик выбора пункта меню настроек. 
    """
    chat_id = callback.from_user.id
    try:
        _, option = callback.data.split(":", 1)
    except ValueError:
        await callback.answer("Неверный формат данных.", show_alert=True)
        return

    if option == "level":
        # Выбор уровня (A1…C2)
        levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
        keyboard = types.InlineKeyboardMarkup(row_width=3)
        for lvl in levels:
            keyboard.add(types.InlineKeyboardButton(lvl, callback_data=f"set_level:{lvl}"))
        await bot.send_message(chat_id, "Выберите уровень:", reply_markup=keyboard)

    elif option == "notifications":
        # Переходим в подменю для уведомлений
        await bot.send_message(chat_id, "Настройки уведомлений:", reply_markup=notification_settings_menu_keyboard())

    elif option == "words":
        # Ожидаем ввод количества слов
        pending_settings[chat_id] = "words"
        await bot.send_message(
            chat_id, 
            "Введите количество слов в день (от 1 до 20):", 
            reply_markup=notification_settings_menu_keyboard()
        )

    elif option == "repetitions":
        # Ожидаем ввод количества повторений
        pending_settings[chat_id] = "repetitions"
        await bot.send_message(
            chat_id, 
            "Введите количество повторений (от 1 до 5):", 
            reply_markup=notification_settings_menu_keyboard()
        )

    elif option == "timezone":
        # Выбор часового пояса с подписью города
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for offset in range(2, 13):
            city_name = timezones_map.get(offset, "")
            tz_label = f"UTC+{offset} {city_name}"  # например, "UTC+3 Москва"
            callback_data = f"set_timezone:UTC+{offset}"
            keyboard.add(types.InlineKeyboardButton(tz_label, callback_data=callback_data))
        
        # Добавляем кнопку «Назад» для возврата в подменю «Настройки уведомлений»
        keyboard.add(
            types.InlineKeyboardButton("Назад", callback_data="settings:notifications")
        )

        await bot.send_message(chat_id, "Выберите ваш часовой пояс:", reply_markup=keyboard)

    elif option == "set":
        # Выбор сета – пока функция в разработке
        await bot.send_message(chat_id, "Эта функция в разработке.", reply_markup=settings_menu_keyboard())

    elif option == "mysettings":
        # Отображаем текущие настройки пользователя
        user = crud.get_user(chat_id)
        if not user:
            await bot.send_message(chat_id, "Профиль не найден. Пожалуйста, используйте /start.")
        else:
            level = user[1]
            words_count = user[2]
            repetitions = user[3]
            timezone = user[5] if len(user) > 5 and user[5] else "Не задан"
            text = (f"Ваш уровень: {level}\n"
                    f"Количество слов в день: {words_count}\n"
                    f"Количество повторений: {repetitions}\n"
                    f"Ваш часовой пояс: {timezone}")
            await bot.send_message(chat_id, text, reply_markup=settings_menu_keyboard())

    await callback.answer()


async def process_set_level_callback(callback: types.CallbackQuery, bot: Bot):
    """
    Устанавливаем уровень пользователя.
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


async def process_set_timezone_callback(callback: types.CallbackQuery, bot: Bot):
    """
    Устанавливаем часовой пояс пользователя (например, "Etc/GMT-3" для UTC+3).
    """
    chat_id = callback.from_user.id
    try:
        _, tz = callback.data.split(":", 1)
    except ValueError:
        await callback.answer("Неверный формат данных.", show_alert=True)
        return

    # tz выглядит как "UTC+3", "UTC+4" и т.д.
    if tz.startswith("UTC+"):
        try:
            offset = int(tz[4:])
            tz_mapped = f"Etc/GMT-{offset}"
        except ValueError:
            tz_mapped = tz
    else:
        tz_mapped = tz

    crud.update_user_timezone(chat_id, tz_mapped)
    if chat_id in daily_words_cache:
        del daily_words_cache[chat_id]

    await bot.send_message(chat_id, f"Часовой пояс установлен на {tz}.",
                           reply_markup=notification_settings_menu_keyboard())
    await callback.answer()


async def process_text_setting(message: types.Message):
    """
    Обработка текстовых ответов, когда бот ожидает количество слов или повторений.
    """
    chat_id = message.chat.id
    if chat_id not in pending_settings:
        return

    setting_type = pending_settings.pop(chat_id)
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("Ошибка: введите корректное число.",
                             reply_markup=notification_settings_menu_keyboard())
        return

    value = int(text)
    if setting_type == "words":
        if not (1 <= value <= 20):
            await message.answer("Ошибка: число должно быть от 1 до 20.",
                                 reply_markup=notification_settings_menu_keyboard())
            return
        crud.update_user_words_per_day(chat_id, value)
        if chat_id in daily_words_cache:
            del daily_words_cache[chat_id]
        await message.answer(f"Количество слов в день установлено на {value}.",
                             reply_markup=notification_settings_menu_keyboard())

    elif setting_type == "repetitions":
        if not (1 <= value <= 5):
            await message.answer("Ошибка: число должно быть от 1 до 5.",
                                 reply_markup=notification_settings_menu_keyboard())
            return
        crud.update_user_notifications(chat_id, value)
        if chat_id in daily_words_cache:
            del daily_words_cache[chat_id]
        await message.answer(f"Количество повторений установлено на {value}.",
                             reply_markup=notification_settings_menu_keyboard())


async def process_notification_back(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик кнопки "Назад" внутри меню уведомлений.
    Возвращает пользователя в главное меню настроек.
    """
    chat_id = callback.from_user.id
    await bot.send_message(chat_id, "Настройки бота:", reply_markup=settings_menu_keyboard())
    await callback.answer()


def register_settings_handlers(dp: Dispatcher, bot: Bot):
    """
    Регистрация всех обработчиков, связанных с настройками.
    """
    # Главное меню настроек
    dp.register_callback_query_handler(
        lambda c: show_settings_callback(c, bot),
        lambda c: c.data == "menu:settings"
    )
    # Кнопка "Назад" из подменю уведомлений
    dp.register_callback_query_handler(
        lambda c: process_notification_back(c, bot),
        lambda c: c.data == "settings:back"
    )
    # Остальные опции "settings:*" (кроме "settings:back")
    dp.register_callback_query_handler(
        lambda c: process_settings_choice_callback(c, bot),
        lambda c: c.data and c.data.startswith("settings:") and c.data != "settings:back"
    )
    # Установка уровня
    dp.register_callback_query_handler(
        lambda c: process_set_level_callback(c, bot),
        lambda c: c.data and c.data.startswith("set_level:")
    )
    # Установка часового пояса
    dp.register_callback_query_handler(
        lambda c: process_set_timezone_callback(c, bot),
        lambda c: c.data and c.data.startswith("set_timezone:")
    )
    # Обработка текстового ввода (количество слов/повторений)
    dp.register_message_handler(process_text_setting, content_types=['text'])
