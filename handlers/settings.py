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
from utils.sticker_helper import get_congratulation_sticker

import urllib.parse


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

        # Get current set and learned words
        current_set = user_set_selection.get(chat_id, None)
        
        # Check if user has any learned words
        try:
            learned_words = crud.get_learned_words(chat_id)
            has_learned_words = len(learned_words) > 0
        except Exception as e:
            logger.error(f"Error checking learned words: {e}")
            has_learned_words = False
        
        # Prepare message with current set info
        message_text = f"Доступные сеты для уровня {user_level}:"
        if current_set:
            message_text = f"Текущий сет: *{current_set}*\n\n" + message_text
        
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for filename in set_files:
            set_name = os.path.splitext(filename)[0]
            # URL-encode the set name to handle special characters safely
            encoded_set_name = urllib.parse.quote(set_name)
            
            # Different callback for different scenarios
            if current_set and set_name != current_set and has_learned_words:
                # User has a set and dictionary, needs confirmation to change
                keyboard.add(types.InlineKeyboardButton(set_name, callback_data=f"confirm_set_change:{encoded_set_name}"))
            else:
                # First selection or no learned words, no confirmation needed
                keyboard.add(types.InlineKeyboardButton(set_name, callback_data=f"choose_set:{encoded_set_name}"))
        
        keyboard.add(types.InlineKeyboardButton("Назад", callback_data="menu:settings"))
        
        await bot.send_message(chat_id, message_text, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Unexpected error in process_my_sets for user {chat_id}: {e}")
        await bot.send_message(chat_id, "Произошла ошибка при получении списка сетов. Пожалуйста, попробуйте позже.")

# Updated process_choose_set function with both fixes for long messages
# and for automatically clearing the dictionary when changing sets

async def process_choose_set(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик выбора сета. Читает файл выбранного сета.
    При большом объеме данных показывает только часть слов.
    При смене сета автоматически очищает словарь пользователя.
    """
    chat_id = callback.from_user.id
    try:
        try:
            _, encoded_set_name = callback.data.split(":", 1)
            # URL-decode the set name to get original name with special characters
            set_name = urllib.parse.unquote(encoded_set_name)
        except ValueError as e:
            logger.error(f"Error parsing callback data: {e}, data: {callback.data}")
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
            logger.warning(f"Unicode decode error in file {set_path}, trying cp1251 encoding")
            try:
                with open(set_path, "r", encoding="cp1251") as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Failed to read file with alternative encoding: {e}")
                await bot.send_message(chat_id, f"Ошибка при чтении файла: неподдерживаемая кодировка.")
                return
        except Exception as e:
            logger.error(f"Error reading file {set_path}: {e}")
            await bot.send_message(chat_id, f"Ошибка при чтении файла: {e}")
            return

        # Проверяем, нужно ли очистить словарь (если это смена сета, а не первичный выбор)
        current_set = user_set_selection.get(chat_id, None)
        dictionary_cleared = False
        
        if current_set and current_set != set_name:
            # Если это смена сета (а не повторный выбор того же сета), очищаем словарь
            try:
                crud.clear_learned_words_for_user(chat_id)
                dictionary_cleared = True
                logger.info(f"Dictionary cleared for user {chat_id} due to set change from '{current_set}' to '{set_name}'")
            except Exception as e:
                logger.error(f"Error clearing dictionary for user {chat_id}: {e}")
        
        # Store the original (non-encoded) set name
        user_set_selection[chat_id] = set_name
        reset_daily_words_cache(chat_id)  # очищаем кэш 'Слова дня' при смене сета
        
        # Проверяем длину сообщения и обрезаем при необходимости
        intro_text = f"Выбран сет {set_name} для уровня {user_level}."
        
        # Добавляем уведомление об очистке словаря, если она произошла
        if dictionary_cleared:
            intro_text += "\n⚠️ Словарь очищен, так как был выбран новый сет."
            
        intro_text += "\nСлова сета:\n\n"
        
        # Разделяем содержимое на отдельные слова
        lines = content.split('\n')
        
        # Telegram ограничивает сообщения до ~4096 символов
        MAX_MESSAGE_LENGTH = 3800  # Оставляем запас для интро и примечания
        
        # Если содержимое слишком большое, показываем только часть
        if len(intro_text) + len(content) > MAX_MESSAGE_LENGTH:
            # Определяем, сколько строк можем показать
            preview_content = ""
            preview_line_count = 0
            word_count = len(lines)
            
            for line in lines:
                if len(intro_text) + len(preview_content) + len(line) + 100 < MAX_MESSAGE_LENGTH:  # +100 для запаса
                    preview_content += line + "\n"
                    preview_line_count += 1
                else:
                    break
            
            note = f"\n\n...и еще {word_count - preview_line_count} слов(а). Полный список будет использован в обучении."
            message_text = intro_text + preview_content + note
        else:
            message_text = intro_text + content

        await bot.send_message(chat_id, message_text, reply_markup=settings_menu_keyboard())
        
    except Exception as e:
        logger.error(f"Unexpected error in process_choose_set for user {chat_id}: {e}")
        await bot.send_message(chat_id, f"Произошла ошибка при выборе сета: {str(e)}. Пожалуйста, попробуйте позже.")
    
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
    """Register all settings handlers"""
    # Basic settings handlers
    dp.register_callback_query_handler(
        partial(show_settings_callback, bot=bot),
        lambda c: c.data == "menu:settings"
    )
    dp.register_callback_query_handler(
        partial(process_notification_back, bot=bot),
        lambda c: c.data == "settings:back"
    )
    dp.register_callback_query_handler(
        partial(process_settings_choice_callback, bot=bot),
        lambda c: c.data and c.data.startswith("settings:") and c.data != "settings:back"
    )
    dp.register_callback_query_handler(
        partial(process_set_level_callback, bot=bot),
        lambda c: c.data and c.data.startswith("set_level:")
    )
    dp.register_callback_query_handler(
        partial(process_set_timezone_callback, bot=bot),
        lambda c: c.data and c.data.startswith("set_timezone:")
    )
    
    # Set change confirmation handlers
    dp.register_callback_query_handler(
        partial(handle_confirm_set_change, bot=bot),
        lambda c: c.data and c.data.startswith("confirm_set_change:")
    )
    dp.register_callback_query_handler(
        partial(handle_set_change_confirmed, bot=bot),
        lambda c: c.data and c.data.startswith("set_change_confirmed:")
    )
    dp.register_callback_query_handler(
        partial(handle_set_change_cancelled, bot=bot),
        lambda c: c.data == "set_change_cancel"
    )
    
    # Final choose_set handler (keep last)
    dp.register_callback_query_handler(
        partial(process_choose_set, bot=bot),
        lambda c: c.data and c.data.startswith("choose_set:")
    )
    
    # Text input handler
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

async def handle_confirm_set_change(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик подтверждения смены сета. 
    Показывает диалог подтверждения с предупреждением о сбросе прогресса.
    """
    chat_id = callback.from_user.id
    try:
        # Extract encoded set name from callback data
        _, encoded_set_name = callback.data.split(":", 1)
        # URL-decode the set name
        set_name = urllib.parse.unquote(encoded_set_name)
        
        # Get current set name
        current_set = user_set_selection.get(chat_id, "не выбран")
        
        # Create confirmation keyboard
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton("✅ Да, сменить", callback_data=f"set_change_confirmed:{encoded_set_name}"),
            types.InlineKeyboardButton("❌ Нет, отмена", callback_data="set_change_cancel")
        )
        
        # Send confirmation message
        await bot.send_message(
            chat_id,
            f"⚠️ *Внимание! Смена сета приведет к полному сбросу прогресса.*\n\n"
            f"Текущий сет: *{current_set}*\n"
            f"Новый сет: *{set_name}*\n\n"
            f"При смене сета ваш словарь будет полностью очищен. Вы уверены?",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in handle_confirm_set_change: {e}")
        await bot.send_message(chat_id, "Произошла ошибка. Пожалуйста, попробуйте позже.")
    
    await callback.answer()

async def handle_set_change_confirmed(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик подтверждения смены сета.
    Очищает словарь и вызывает функцию выбора сета.
    """
    chat_id = callback.from_user.id
    try:
        # Extract the encoded set name
        _, encoded_set_name = callback.data.split(":", 1)
        set_name = urllib.parse.unquote(encoded_set_name)
        
        # Clear user's dictionary
        try:
            crud.clear_learned_words_for_user(chat_id)
            logger.info(f"Dictionary cleared for user {chat_id} due to set change")
        except Exception as e:
            logger.error(f"Error clearing dictionary: {e}")
            await bot.send_message(chat_id, "Произошла ошибка при очистке словаря. Пожалуйста, попробуйте позже.")
            await callback.answer()
            return
        
        # Get user level
        user = crud.get_user(chat_id)
        if not user:
            await bot.send_message(chat_id, "Профиль не найден. Используйте /start.")
            await callback.answer()
            return
            
        user_level = user[1]
        set_path = os.path.join(LEVELS_DIR, user_level, f"{set_name}.txt")
        
        if not os.path.exists(set_path):
            logger.warning(f"Set file not found: {set_path}")
            await bot.send_message(chat_id, f"Сет {set_name} не найден для уровня {user_level}.")
            await callback.answer()
            return
        
        # Read file content
        try:
            with open(set_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(set_path, "r", encoding="cp1251") as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Error reading file: {e}")
                await bot.send_message(chat_id, f"Ошибка при чтении файла. Пожалуйста, попробуйте позже.")
                await callback.answer()
                return
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            await bot.send_message(chat_id, f"Ошибка при чтении файла. Пожалуйста, попробуйте позже.")
            await callback.answer()
            return
        
        # Store the selected set and reset cache
        user_set_selection[chat_id] = set_name
        reset_daily_words_cache(chat_id)
        
        # Store the selected set and reset cache
        user_set_selection[chat_id] = set_name
        reset_daily_words_cache(chat_id)
        
        # Отправляем стикер для смены уровня
        sticker_id = get_congratulation_sticker()
        if sticker_id:
            await bot.send_sticker(chat_id, sticker_id)

        # Format message with truncation for large sets
        intro_text = f"Выбран сет {set_name} для уровня {user_level}.\n⚠️ Словарь успешно очищен.\nСлова сета:\n\n"
        
        # Split content into lines
        lines = content.split('\n')
        
        # Max message length for Telegram
        MAX_MESSAGE_LENGTH = 3800
        
        # Check if content is too large
        if len(intro_text) + len(content) > MAX_MESSAGE_LENGTH:
            preview_content = ""
            preview_line_count = 0
            word_count = len(lines)
            
            for line in lines:
                if len(intro_text) + len(preview_content) + len(line) + 100 < MAX_MESSAGE_LENGTH:
                    preview_content += line + "\n"
                    preview_line_count += 1
                else:
                    break
            
            note = f"\n\n...и еще {word_count - preview_line_count} слов(а). Полный список будет использован в обучении."
            message_text = intro_text + preview_content + note
        else:
            message_text = intro_text + content
        
        # Send the message
        await bot.send_message(chat_id, message_text, reply_markup=settings_menu_keyboard())
        
    except Exception as e:
        logger.error(f"Error in handle_set_change_confirmed: {e}")
        await bot.send_message(chat_id, f"Произошла ошибка при смене сета: {str(e)}. Пожалуйста, попробуйте позже.")
    
    await callback.answer()


async def handle_set_change_cancelled(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик отмены смены сета.
    Возвращает к списку сетов.
    """
    chat_id = callback.from_user.id
    
    # Возвращаемся к списку сетов
    await process_my_sets(callback, bot)
    await callback.answer("Смена сета отменена")