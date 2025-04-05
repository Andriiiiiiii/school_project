from aiogram import types, Dispatcher, Bot
from keyboards.submenus import (
    notification_settings_menu_keyboard, 
    settings_menu_keyboard
)
from keyboards.main_menu import main_menu_keyboard
from database import crud
from functools import partial
from utils.helpers import reset_daily_words_cache, LEVELS_DIR
import os
import logging
from zoneinfo import ZoneInfo

from utils.visual_helpers import format_settings_overview


# Настройка логирования
logger = logging.getLogger(__name__)

# Глобальный словарь для хранения состояния ввода (какой параметр ожидается от пользователя)
pending_settings = {}

# Глобальный словарь для хранения выбранного сета пользователем (ключ: chat_id, значение: имя сета)
user_set_selection = {}

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

# Словарь соответствия российских часовых поясов стандартным IANA идентификаторам
russian_tzs = {
    2: "Europe/Kaliningrad",  # UTC+2
    3: "Europe/Moscow",       # UTC+3
    4: "Europe/Samara",       # UTC+4
    5: "Asia/Yekaterinburg",  # UTC+5
    6: "Asia/Omsk",           # UTC+6
    7: "Asia/Krasnoyarsk",    # UTC+7
    8: "Asia/Irkutsk",        # UTC+8
    9: "Asia/Yakutsk",        # UTC+9
    10: "Asia/Vladivostok",   # UTC+10
    11: "Asia/Magadan",       # UTC+11
    12: "Asia/Kamchatka"      # UTC+12
}

def is_valid_timezone(tz_name):
    """Проверяет валидность часового пояса."""
    try:
        ZoneInfo(tz_name)
        return True
    except Exception:
        return False

async def show_settings_callback(callback: types.CallbackQuery, bot: Bot):
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
        levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
        keyboard = types.InlineKeyboardMarkup(row_width=3)
        for lvl in levels:
            keyboard.add(types.InlineKeyboardButton(lvl, callback_data=f"set_level:{lvl}"))
        await bot.send_message(chat_id, "Выберите уровень:", reply_markup=keyboard)

    elif option == "notifications":
        await bot.send_message(chat_id, "Настройки уведомлений:", reply_markup=notification_settings_menu_keyboard())

    elif option == "words":
        pending_settings[chat_id] = "words"
        await bot.send_message(chat_id, "Введите количество слов в день (от 1 до 20):", reply_markup=notification_settings_menu_keyboard())

    elif option == "repetitions":
        pending_settings[chat_id] = "repetitions"
        await bot.send_message(chat_id, "Введите количество повторений (от 1 до 5):", reply_markup=notification_settings_menu_keyboard())

    elif option == "timezone":
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for offset in range(2, 13):
            city_name = timezones_map.get(offset, "")
            tz_label = f"UTC+{offset} {city_name}"
            callback_data = f"set_timezone:UTC+{offset}"
            keyboard.add(types.InlineKeyboardButton(tz_label, callback_data=callback_data))
        keyboard.add(types.InlineKeyboardButton("Назад", callback_data="settings:notifications"))
        await bot.send_message(chat_id, "Выберите ваш часовой пояс:", reply_markup=keyboard)

    elif option == "set":
        await process_my_sets(callback, bot)

    elif option == "mysettings":
        user = crud.get_user(chat_id)
        if not user:
            await bot.send_message(chat_id, "Профиль не найден. Пожалуйста, используйте /start.")
        else:
            level = user[1]
            words_count = user[2]
            repetitions = user[3]
            timezone = user[5] if len(user) > 5 and user[5] else "Не задан"
            set_info = f"\nВыбранный сет: {user_set_selection.get(chat_id, 'Не выбран')}"
            text = (f"Ваш уровень: {level}\n"
                    f"Количество слов в день: {words_count}\n"
                    f"Количество повторений: {repetitions}\n"
                    f"Ваш часовой пояс: {timezone}" + set_info)
            await bot.send_message(chat_id, text, reply_markup=settings_menu_keyboard())

    await callback.answer()

async def process_my_sets(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик кнопки "Мои сеты". Сканирует папку для текущего уровня пользователя.
    """
    chat_id = callback.from_user.id
    try:
        user = crud.get_user(chat_id)
        if not user:
            await bot.send_message(chat_id, "Профиль не найден. Пожалуйста, используйте /start.")
            return
            
        user_level = user[1]
        level_dir = os.path.join(LEVELS_DIR, user_level)
        
        if not os.path.exists(level_dir):
            logger.warning(f"Level directory not found: {level_dir}")
            await bot.send_message(chat_id, f"Папка для уровня {user_level} не найдена.")
            return
            
        try:
            set_files = [f for f in os.listdir(level_dir) if f.endswith(".txt")]
        except PermissionError:
            logger.error(f"Permission denied when accessing directory: {level_dir}")
            await bot.send_message(chat_id, f"Ошибка доступа к папке уровня {user_level}.")
            return
        except Exception as e:
            logger.error(f"Error listing directory {level_dir}: {e}")
            await bot.send_message(chat_id, f"Ошибка при чтении папки уровня {user_level}.")
            return
            
        if not set_files:
            await bot.send_message(chat_id, f"В папке {user_level} не найдено сетов.")
            return

        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for filename in set_files:
            set_name = os.path.splitext(filename)[0]
            keyboard.add(types.InlineKeyboardButton(set_name, callback_data=f"choose_set:{set_name}"))
        keyboard.add(types.InlineKeyboardButton("Назад", callback_data="menu:settings"))
        
        await bot.send_message(chat_id, f"Доступные сеты для уровня {user_level}:", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Unexpected error in process_my_sets for user {chat_id}: {e}")
        await bot.send_message(chat_id, "Произошла ошибка при получении списка сетов. Пожалуйста, попробуйте позже.")
    
async def process_choose_set(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик выбора сета. Читает файл выбранного сета.
    """
    chat_id = callback.from_user.id
    try:
        try:
            _, set_name = callback.data.split(":", 1)
        except ValueError:
            await callback.answer("Неверный формат данных.", show_alert=True)
            return

        user = crud.get_user(chat_id)
        if not user:
            await bot.send_message(chat_id, "Профиль не найден. Используйте /start.")
            return

        user_level = user[1]
        set_path = os.path.join(LEVELS_DIR, user_level, f"{set_name}.txt")
        
        if not os.path.exists(set_path):
            logger.warning(f"Set file not found: {set_path}")
            await bot.send_message(chat_id, f"Сет {set_name} не найден для уровня {user_level}.")
            return
        
        content = ""
        try:
            with open(set_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            logger.warning(f"Unicode decode error for file {set_path}, trying cp1251 encoding")
            try:
                with open(set_path, "r", encoding="cp1251") as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Failed to read file with alternative encoding: {e}")
                await bot.send_message(chat_id, f"Ошибка при чтении файла: неподдерживаемая кодировка.")
                return
        except PermissionError:
            logger.error(f"Permission denied when reading file: {set_path}")
            await bot.send_message(chat_id, f"Ошибка доступа при чтении файла.")
            return
        except Exception as e:
            logger.error(f"Error reading file {set_path}: {e}")
            await bot.send_message(chat_id, f"Ошибка при чтении файла: {e}")
            return

        user_set_selection[chat_id] = set_name
        reset_daily_words_cache(chat_id)  # очищаем кэш 'Слова дня' при смене сета

        await bot.send_message(chat_id, f"Выбран сет {set_name} для уровня {user_level}.\nСлова сета:\n\n{content}",
                                  reply_markup=settings_menu_keyboard())
    except Exception as e:
        logger.error(f"Unexpected error in process_choose_set for user {chat_id}: {e}")
        await bot.send_message(chat_id, "Произошла ошибка при выборе сета. Пожалуйста, попробуйте позже.")
    
    await callback.answer()

async def process_set_level_callback(callback: types.CallbackQuery, bot: Bot):
    chat_id = callback.from_user.id
    try:
        _, level = callback.data.split(":", 1)
    except ValueError:
        await callback.answer("Неверный формат данных.", show_alert=True)
        return
    crud.update_user_level(chat_id, level)
    reset_daily_words_cache(chat_id)
    await bot.send_message(chat_id, f"Уровень установлен на {level}.", reply_markup=settings_menu_keyboard())
    await callback.answer()

async def process_set_timezone_callback(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик выбора часового пояса. Корректно преобразует UTC+X в стандартный IANA идентификатор.
    """
    chat_id = callback.from_user.id
    try:
        _, tz = callback.data.split(":", 1)
    except ValueError:
        await callback.answer("Неверный формат данных.", show_alert=True)
        return
    
    # Преобразуем формат UTC+ в стандартный IANA формат
    if tz.startswith("UTC+"):
        try:
            offset = int(tz[4:])
            
            # Используем российские часовые пояса, где это возможно
            if offset in russian_tzs:
                tz_mapped = russian_tzs[offset]
            else:
                # Правильное преобразование: UTC+X соответствует Etc/GMT-X 
                # (в POSIX знак инвертирован)
                tz_mapped = f"Etc/GMT-{offset}"
                
            # Проверяем валидность полученного часового пояса
            if not is_valid_timezone(tz_mapped):
                logger.warning(f"Невалидный часовой пояс {tz_mapped} для пользователя {chat_id}")
                tz_mapped = "Europe/Moscow"  # Значение по умолчанию
        except ValueError:
            logger.error(f"Ошибка преобразования часового пояса {tz} для пользователя {chat_id}")
            tz_mapped = "Europe/Moscow"  # Значение по умолчанию при ошибке
    else:
        tz_mapped = tz
        # Проверяем валидность если пояс передан напрямую
        if not is_valid_timezone(tz_mapped):
            logger.warning(f"Невалидный часовой пояс {tz_mapped} для пользователя {chat_id}")
            tz_mapped = "Europe/Moscow"  # Значение по умолчанию
    
    crud.update_user_timezone(chat_id, tz_mapped)
    reset_daily_words_cache(chat_id)
    await bot.send_message(chat_id, f"Часовой пояс установлен на {tz}.", reply_markup=notification_settings_menu_keyboard())
    await callback.answer()

async def process_text_setting(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in pending_settings:
        return
    setting_type = pending_settings.pop(chat_id)
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("Ошибка: введите корректное число.", reply_markup=notification_settings_menu_keyboard())
        return
    value = int(text)
    if setting_type == "words":
        if not (1 <= value <= 20):
            await message.answer("Ошибка: число должно быть от 1 до 20.", reply_markup=notification_settings_menu_keyboard())
            return
        crud.update_user_words_per_day(chat_id, value)
        reset_daily_words_cache(chat_id)
        await message.answer(f"Количество слов в день установлено на {value}.", reply_markup=notification_settings_menu_keyboard())
    elif setting_type == "repetitions":
        if not (1 <= value <= 5):
            await message.answer("Ошибка: число должно быть от 1 до 5.", reply_markup=notification_settings_menu_keyboard())
            return
        crud.update_user_notifications(chat_id, value)
        reset_daily_words_cache(chat_id)
        await message.answer(f"Количество повторений установлено на {value}.", reply_markup=notification_settings_menu_keyboard())

async def process_notification_back(callback: types.CallbackQuery, bot: Bot):
    chat_id = callback.from_user.id
    await bot.send_message(chat_id, "Настройки бота:", reply_markup=settings_menu_keyboard())
    await callback.answer()

def register_settings_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(
        lambda c: show_settings_callback(c, bot),
        lambda c: c.data == "menu:settings"
    )
    dp.register_callback_query_handler(
        lambda c: process_notification_back(c, bot),
        lambda c: c.data == "settings:back"
    )
    dp.register_callback_query_handler(
        lambda c: process_settings_choice_callback(c, bot),
        lambda c: c.data and c.data.startswith("settings:") and c.data != "settings:back"
    )
    dp.register_callback_query_handler(
        lambda c: process_set_level_callback(c, bot),
        lambda c: c.data and c.data.startswith("set_level:")
    )
    dp.register_callback_query_handler(
        lambda c: process_set_timezone_callback(c, bot),
        lambda c: c.data and c.data.startswith("set_timezone:")
    )
    dp.register_callback_query_handler(
        lambda c: process_choose_set(c, bot),
        lambda c: c.data and c.data.startswith("choose_set:")
    )
    dp.register_message_handler(process_text_setting, content_types=['text'])

async def process_settings_mysettings(callback: types.CallbackQuery, bot: Bot):
    """Display user settings with enhanced formatting"""
    chat_id = callback.from_user.id
    user = crud.get_user(chat_id)
    
    if not user:
        await bot.send_message(
            chat_id, 
            "⚠️ Profile not found. Please use /start.",
            parse_mode="Markdown"
        )
    else:
        # Create a dictionary of user settings
        user_settings = {
            "level": user[1],
            "words_per_day": user[2],
            "repetitions": user[3],
            "timezone": user[5] if len(user) > 5 and user[5] else "Not set",
            "chosen_set": user_set_selection.get(chat_id, "Not selected")
        }
        
        # Use the visual helper to format the settings
        formatted_settings = format_settings_overview(user_settings)
        
        await bot.send_message(
            chat_id, 
            formatted_settings,
            parse_mode="Markdown", 
            reply_markup=settings_menu_keyboard()
        )