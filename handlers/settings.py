from aiogram import types, Dispatcher, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.submenus import (
    notification_settings_menu_keyboard, 
    settings_menu_keyboard,
    level_selection_keyboard  # Добавляем импорт для функции выбора уровня
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

from config import DEFAULT_SETS

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
    """Редактируем сообщение вместо отправки нового"""
    await callback.message.edit_text("Настройки бота:", reply_markup=settings_menu_keyboard())
    await callback.answer()

async def process_settings_choice_callback(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик выбора пункта меню настроек.
    Обновлен для использования новых клавиатур и улучшенного UX.
    """
    chat_id = callback.from_user.id
    try:
        _, option = callback.data.split(":", 1)
    except ValueError:
        await callback.answer("Неверный формат данных.", show_alert=True)
        return

    if option == "level":
        # Используем функцию выбора уровня
        await callback.message.edit_text(
            "🔤 *Выберите уровень сложности:*\n\n"
            "🟢 *A1-A2* - Начальный уровень\n"
            "🟡 *B1-B2* - Средний уровень\n"
            "🔴 *C1-C2* - Продвинутый уровень", 
            parse_mode="Markdown",
            reply_markup=level_selection_keyboard()
        )

    elif option == "notifications":
        await callback.message.edit_text(
            "⚙️ *Настройки уведомлений*\n\n"
            "Здесь вы можете настроить частоту и количество уведомлений, "
            "а также свой часовой пояс для правильного времени доставки.",
            parse_mode="Markdown",
            reply_markup=notification_settings_menu_keyboard()
        )

    elif option == "words":
        pending_settings[chat_id] = "words"
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="settings:back"))
        
        await callback.message.edit_text(
            "📊 *Количество слов в день*\n\n"
            "Выберите оптимальное количество новых слов для изучения ежедневно. "
            "Рекомендуется от 5 до 15 слов для эффективного обучения.\n\n"
            "Введите число от 1 до 20:",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    elif option == "repetitions":
        pending_settings[chat_id] = "repetitions"
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="settings:back"))
        
        await callback.message.edit_text(
            "🔄 *Количество повторений*\n\n"
            "Выберите, сколько раз вы хотите повторять каждое слово в течение дня. "
            "Повторение помогает лучше запомнить слова.\n\n"
            "Введите число от 1 до 5:",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    elif option == "timezone":
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        for offset in range(2, 13):
            city_name = timezones_map.get(offset, "")
            tz_label = f"UTC+{offset} {city_name}"
            callback_data = f"set_timezone:UTC+{offset}"
            
            keyboard.insert(InlineKeyboardButton(tz_label, callback_data=callback_data))
            
        # Добавляем кнопку Назад
        keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="settings:back"))
        
        await callback.message.edit_text(
            "🌐 *Выберите ваш часовой пояс*\n\n"
            "Это позволит отправлять уведомления в удобное для вас время.",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    elif option == "set":
        await process_my_sets(callback, bot)

    elif option == "mysettings":
        # Обновленная функция для более красивого отображения настроек
        await process_settings_mysettings(callback, bot)

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
        
        logger.info(f"Проверка директории сетов для пользователя {chat_id}, уровень {user_level}, путь: {level_dir}")
        
        if not os.path.exists(level_dir):
            logger.warning(f"Level directory not found: {level_dir}")
            await bot.send_message(chat_id, f"Папка для уровня {user_level} не найдена.")
            return
            
        try:
            set_files = [f for f in os.listdir(level_dir) if f.endswith(".txt")]
            logger.info(f"Найдено {len(set_files)} файлов сетов в директории {level_dir}")
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
        
        # Если не в кэше, смотрим в базе данных
        if not current_set and len(user) > 6 and user[6]:
            current_set = user[6]
            # Обновляем кэш для согласованности
            user_set_selection[chat_id] = current_set
        
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
        
        # Ограничиваем длину callback_data, чтобы избежать ошибки Button_data_invalid
        for filename in set_files:
            set_name = os.path.splitext(filename)[0]
            
            # Используем индекс вместо имени сета в callback_data для предотвращения ошибки
            # Сохраняем соответствие в кэше
            set_index = len(set_files) - set_files.index(filename)  # Начинаем с 1
            callback_data = f"set_idx:{set_index}" if not has_learned_words else f"confirm_idx:{set_index}"
            
            # Сохраняем имя сета в глобальный cache для восстановления по индексу
            if not hasattr(process_my_sets, 'set_cache'):
                process_my_sets.set_cache = {}
            process_my_sets.set_cache[f"{chat_id}_{set_index}"] = set_name
            
            keyboard.add(types.InlineKeyboardButton(set_name, callback_data=callback_data))
        
        keyboard.add(types.InlineKeyboardButton("Назад", callback_data="menu:settings"))
        
        await bot.send_message(chat_id, message_text, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Необработанная ошибка в process_my_sets для пользователя {chat_id}: {e}")
        await bot.send_message(chat_id, "Произошла ошибка при получении списка сетов. Пожалуйста, попробуйте позже или обратитесь к администратору.")

async def handle_set_by_index(callback: types.CallbackQuery, bot: Bot):
    """Обработчик выбора сета по индексу"""
    chat_id = callback.from_user.id
    try:
        _, set_index = callback.data.split(":", 1)
        set_index = int(set_index)
        
        # Получаем имя сета из кэша
        if not hasattr(process_my_sets, 'set_cache'):
            process_my_sets.set_cache = {}
        
        set_name = process_my_sets.set_cache.get(f"{chat_id}_{set_index}")
        if not set_name:
            await callback.answer("Ошибка: информация о сете не найдена. Пожалуйста, попробуйте снова.")
            return
        
        # Получаем пользователя и его уровень
        user = crud.get_user(chat_id)
        if not user:
            await callback.answer("Профиль не найден. Используйте /start.")
            return
        
        user_level = user[1]
        
        # Получаем текущий выбранный сет
        current_set = None
        if chat_id in user_set_selection:
            current_set = user_set_selection[chat_id]
        
        # Если нет в кэше, смотрим в базе данных
        if not current_set and len(user) > 6 and user[6]:
            current_set = user[6]
        
        # Проверяем, является ли это сменой сета
        is_change = current_set and current_set != set_name
        
        # Обновляем сет в бд и кэше
        crud.update_user_chosen_set(chat_id, set_name)
        user_set_selection[chat_id] = set_name
        reset_daily_words_cache(chat_id)
        
        # Если это смена сета, очищаем словарь
        if is_change:
            crud.clear_learned_words_for_user(chat_id)
        
        # Отправляем сообщение об успешном выборе сета
        await callback.message.edit_text(
            f"✅ Выбран сет '{set_name}' для уровня {user_level}.\n\n"
            f"{'⚠️ Словарь очищен, так как был выбран новый сет.' if is_change else ''}",
            parse_mode="Markdown",
            reply_markup=settings_menu_keyboard()
        )
        
    except ValueError:
        await callback.answer("Неверный формат данных.")
    except Exception as e:
        logger.error(f"Ошибка при выборе сета по индексу: {e}")
        await callback.answer("Произошла ошибка при выборе сета.")

async def handle_confirm_set_by_index(callback: types.CallbackQuery, bot: Bot):
    """Обработчик подтверждения смены сета по индексу"""
    chat_id = callback.from_user.id
    try:
        _, set_index = callback.data.split(":", 1)
        set_index = int(set_index)
        
        # Получаем имя сета из кэша
        if not hasattr(process_my_sets, 'set_cache'):
            process_my_sets.set_cache = {}
        
        set_name = process_my_sets.set_cache.get(f"{chat_id}_{set_index}")
        if not set_name:
            await callback.answer("Ошибка: информация о сете не найдена. Пожалуйста, попробуйте снова.")
            return
        
        # Получаем текущий выбранный сет
        current_set = None
        if chat_id in user_set_selection:
            current_set = user_set_selection[chat_id]
        
        # Если нет в кэше, смотрим в базе данных
        user = crud.get_user(chat_id)
        if not current_set and user and len(user) > 6 and user[6]:
            current_set = user[6]
        
        # Создаем клавиатуру для подтверждения
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton("✅ Да, сменить", callback_data=f"set_chg_idx:{set_index}"),
            types.InlineKeyboardButton("❌ Нет, отмена", callback_data="set_change_cancel")
        )
        
        # Отправляем сообщение с подтверждением
        await callback.message.edit_text(
            f"⚠️ *Внимание! Смена сета приведет к полному сбросу прогресса.*\n\n"
            f"Текущий сет: *{current_set}*\n"
            f"Новый сет: *{set_name}*\n\n"
            f"При смене сета ваш словарь будет полностью очищен. Вы уверены?",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except ValueError:
        await callback.answer("Неверный формат данных.")
    except Exception as e:
        logger.error(f"Ошибка при подтверждении смены сета: {e}")
        await callback.answer("Произошла ошибка при подготовке подтверждения.")

async def handle_set_change_confirmed_by_index(callback: types.CallbackQuery, bot: Bot):
    """Обработчик подтвержденной смены сета по индексу"""
    chat_id = callback.from_user.id
    try:
        _, set_index = callback.data.split(":", 1)
        set_index = int(set_index)
        
        # Получаем имя сета из кэша
        if not hasattr(process_my_sets, 'set_cache'):
            process_my_sets.set_cache = {}
        
        set_name = process_my_sets.set_cache.get(f"{chat_id}_{set_index}")
        if not set_name:
            await callback.answer("Ошибка: информация о сете не найдена. Пожалуйста, попробуйте снова.")
            return
        
        # Очищаем словарь пользователя
        crud.clear_learned_words_for_user(chat_id)
        
        # Обновляем выбранный сет
        crud.update_user_chosen_set(chat_id, set_name)
        user_set_selection[chat_id] = set_name
        reset_daily_words_cache(chat_id)
        
        # Отправляем стикер
        from utils.sticker_helper import get_congratulation_sticker
        sticker_id = get_congratulation_sticker()
        if sticker_id:
            await bot.send_sticker(chat_id, sticker_id)
        
        # Отправляем сообщение об успешной смене сета
        await callback.message.edit_text(
            f"✅ Выбран сет '{set_name}'.\n⚠️ Словарь успешно очищен.",
            reply_markup=settings_menu_keyboard()
        )
        
    except ValueError:
        await callback.answer("Неверный формат данных.")
    except Exception as e:
        logger.error(f"Ошибка при подтвержденной смене сета: {e}")
        await callback.answer("Произошла ошибка при смене сета.")

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
        
        logger.info(f"Проверка пути к файлу сета: {set_path} для пользователя {chat_id}")
        
        # Проверяем существование файла сета
        if not os.path.exists(set_path):
            # Проверяем, может файл существует с другим регистром
            parent_dir = os.path.dirname(set_path)
            file_name = os.path.basename(set_path)
            
            if os.path.exists(parent_dir):
                try:
                    files = os.listdir(parent_dir)
                    for file in files:
                        if file.lower() == file_name.lower():
                            set_path = os.path.join(parent_dir, file)
                            logger.info(f"Найден файл с другим регистром: {set_path}")
                            break
                except Exception as e:
                    logger.error(f"Ошибка при поиске файла с другим регистром: {e}")
            
            if not os.path.exists(set_path):
                logger.warning(f"Set file not found: {set_path}")
                await bot.send_message(chat_id, f"Сет {set_name} не найден для уровня {user_level}. Пожалуйста, выберите другой сет.")
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
    
    # Получаем текущего пользователя
    user = crud.get_user(chat_id)
    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    
    # Проверяем текущий сет пользователя
    current_set = None
    if chat_id in user_set_selection:
        current_set = user_set_selection[chat_id]
    
    # Если нет в кэше, смотрим в базе данных
    if not current_set and len(user) > 6 and user[6]:
        current_set = user[6]
    
    # Обновляем уровень
    crud.update_user_level(chat_id, level)
    
    # Если сет не выбран, устанавливаем базовый для нового уровня
    if not current_set:
        default_set = DEFAULT_SETS.get(level)
        if default_set:
            try:
                crud.update_user_chosen_set(chat_id, default_set)
                user_set_selection[chat_id] = default_set
                current_set = default_set
                logger.info(f"Установлен базовый сет {default_set} для пользователя {chat_id} при смене уровня на {level}")
            except Exception as e:
                logger.error(f"Ошибка при установке базового сета для пользователя {chat_id}: {e}")
    
    # Сбрасываем кэш ежедневных слов
    reset_daily_words_cache(chat_id)
    
    set_info = f"\nТекущий набор слов: {current_set}" if current_set else ""
    await bot.send_message(chat_id, f"Уровень установлен на {level}.{set_info}", reply_markup=settings_menu_keyboard())
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
    """Исправление: Редактируем существующее сообщение вместо отправки нового"""
    await callback.message.edit_text("Настройки бота:", reply_markup=settings_menu_keyboard())
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
    
    # Новые обработчики для выбора сета по индексу
    dp.register_callback_query_handler(
        partial(handle_set_by_index, bot=bot),
        lambda c: c.data and c.data.startswith("set_idx:")
    )
    dp.register_callback_query_handler(
        partial(handle_confirm_set_by_index, bot=bot),
        lambda c: c.data and c.data.startswith("confirm_idx:")
    )
    dp.register_callback_query_handler(
        partial(handle_set_change_confirmed_by_index, bot=bot),
        lambda c: c.data and c.data.startswith("set_chg_idx:")
    )
    
    # Final choose_set handler (keep last)
    dp.register_callback_query_handler(
        partial(process_choose_set, bot=bot),
        lambda c: c.data and c.data.startswith("choose_set:")
    )
    
    # Text input handler
    dp.register_message_handler(process_text_setting, content_types=['text'])


async def process_settings_mysettings(callback: types.CallbackQuery, bot: Bot):
    """Отображает настройки пользователя с улучшенным форматированием"""
    chat_id = callback.from_user.id
    user = crud.get_user(chat_id)
    
    if not user:
        await callback.message.edit_text(
            "⚠️ *Профиль не найден.*\n\nПожалуйста, используйте /start.",
            parse_mode="Markdown",
            reply_markup=types.InlineKeyboardMarkup().add(
                InlineKeyboardButton("🔙 Назад", callback_data="menu:back")
            )
        )
    else:
        # Проверяем и устанавливаем базовый сет, если отсутствует
        current_set = None
        
        # Проверяем сет в кэше
        if chat_id in user_set_selection:
            current_set = user_set_selection[chat_id]
        
        # Если нет в кэше, смотрим в базе данных
        if not current_set and len(user) > 6 and user[6]:
            current_set = user[6]
        
        # Если сет до сих пор не определен, устанавливаем базовый
        if not current_set:
            level = user[1]
            default_set = DEFAULT_SETS.get(level)
            if default_set:
                try:
                    crud.update_user_chosen_set(chat_id, default_set)
                    user_set_selection[chat_id] = default_set
                    current_set = default_set
                    logger.info(f"Установлен базовый сет {default_set} для пользователя {chat_id} при просмотре профиля")
                except Exception as e:
                    logger.error(f"Ошибка при установке базового сета для пользователя {chat_id}: {e}")
        
        # Создаем словарь настроек пользователя
        user_settings = {
            "level": user[1],
            "words_per_day": user[2],
            "repetitions": user[3],
            "timezone": user[5] if len(user) > 5 and user[5] else "Не задан",
            "chosen_set": current_set or "Не выбран"
        }
        
        # Красивое форматирование
        message = "👤 *Ваш профиль*\n\n"
        message += f"🔤 *Уровень:* {user_settings['level']}\n"
        message += f"📊 *Слов в день:* {user_settings['words_per_day']}\n"
        message += f"🔄 *Повторений:* {user_settings['repetitions']}\n"
        message += f"🌐 *Часовой пояс:* {user_settings['timezone']}\n"
        message += f"📚 *Выбранный набор:* {user_settings['chosen_set']}\n\n"
        
        # Добавляем статистику, если есть
        try:
            learned_words = crud.get_learned_words(chat_id)
            message += f"📈 *Статистика*\n"
            message += f"📝 Выучено слов: {len(learned_words)}\n"
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
        
        await callback.message.edit_text(
            message,
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