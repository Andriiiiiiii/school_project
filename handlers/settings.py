# handlers/settings.py - начало файла с импортами
from aiogram import types, Dispatcher, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.submenus import (
    notification_settings_menu_keyboard, 
    settings_menu_keyboard,
    level_selection_keyboard
)
from keyboards.main_menu import main_menu_keyboard
from database import crud
from functools import partial
from utils.helpers import reset_daily_words_cache, extract_english
import os
import logging
from zoneinfo import ZoneInfo
import sqlite3
from config import DEFAULT_SETS, DB_PATH, LEVELS_DIR
from utils.visual_helpers import format_progress_bar

# Настройка логирования
logger = logging.getLogger(__name__)

# Глобальный словарь для хранения состояния ввода
pending_settings = {}

# Глобальный словарь для хранения выбранного сета пользователем
user_set_selection = {}

# Глобальный словарь для хранения индексов и имен сетов
set_index_cache = {}

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

settings_input_state = {}

async def process_settings_input(message: types.Message, bot: Bot):
    """Полностью переработанный обработчик ввода настроек."""
    chat_id = message.chat.id
    text = message.text.strip()
    
    # Сразу добавляем отладочную информацию
    logger.info(f"Получено сообщение от {chat_id}: '{text}'")
    logger.info(f"Текущие состояния ожидания ввода: {pending_settings}")
    
    # Проверка на числовой ввод
    if not text.isdigit():
        if chat_id in pending_settings:
            await message.answer(
                "⚠️ Ошибка: пожалуйста, введите число.",
                reply_markup=notification_settings_menu_keyboard()
            )
            return True
        return False
    
    # Числовой ввод получен, проверяем, ожидается ли он
    if chat_id not in pending_settings:
        logger.info(f"Пользователь {chat_id} не в режиме ожидания ввода")
        return False
    
    value = int(text)
    setting_type = pending_settings[chat_id]
    logger.info(f"Обработка ввода для настройки {setting_type}: {value}")
    
    # Обработка ввода количества слов
    if setting_type == "words":
        # Проверка диапазона
        if not (1 <= value <= 20):
            await message.answer(
                "⚠️ Ошибка: число должно быть от 1 до 20.",
                reply_markup=notification_settings_menu_keyboard()
            )
            return True
        
        # Обновление в базе данных с дополнительной защитой от ошибок
        try:
            # Получаем текущие настройки для сравнения "до" и "после"
            user_before = crud.get_user(chat_id)
            current_words_before = user_before[2] if user_before else 5
            
            # Напрямую используем транзакцию через db_manager
            with db_manager.transaction() as conn:
                conn.execute(
                    "UPDATE users SET words_per_day = ? WHERE chat_id = ?",
                    (value, chat_id)
                )
            
            # Проверяем, произошло ли обновление
            user_after = crud.get_user(chat_id)
            current_words_after = user_after[2] if user_after else current_words_before
            
            # Если обновление не произошло, повторяем через crud
            if current_words_after == current_words_before:
                logger.warning(f"Первая попытка обновления не сработала, пробуем через crud")
                crud.update_user_words_per_day(chat_id, value)
                user_after = crud.get_user(chat_id)
                current_words_after = user_after[2] if user_after else current_words_before
            
            logger.info(f"Значение words_per_day обновлено: {current_words_before} -> {current_words_after}")
            
            # Сбрасываем кэш и состояние
            reset_daily_words_cache(chat_id)
            del pending_settings[chat_id]
            
            # Получаем текущие настройки для отображения
            current_repetitions = user_after[3] if user_after else 3
            
            # Отправляем подтверждение
            await message.answer(
                f"✅ Настройки успешно обновлены!\n\n"
                f"📊 Количество слов в день: *{current_words_after}*\n"
                f"🔄 Количество повторений: *{current_repetitions}*",
                parse_mode="Markdown",
                reply_markup=notification_settings_menu_keyboard()
            )
        except Exception as e:
            logger.error(f"Ошибка при обновлении количества слов: {e}")
            await message.answer(
                "❌ Произошла ошибка при обновлении настроек.",
                reply_markup=notification_settings_menu_keyboard()
            )
        
        return True
        
    # Обработка ввода количества повторений
    elif setting_type == "repetitions":
        # Проверка диапазона
        if not (1 <= value <= 5):
            await message.answer(
                "⚠️ Ошибка: число должно быть от 1 до 5.",
                reply_markup=notification_settings_menu_keyboard()
            )
            return True
        
        # Обновление в базе данных с дополнительной защитой от ошибок
        try:
            # Получаем текущие настройки для сравнения "до" и "после"
            user_before = crud.get_user(chat_id)
            current_repetitions_before = user_before[3] if user_before else 3
            
            # Напрямую используем транзакцию через db_manager
            with db_manager.transaction() as conn:
                conn.execute(
                    "UPDATE users SET notifications = ? WHERE chat_id = ?",
                    (value, chat_id)
                )
            
            # Проверяем, произошло ли обновление
            user_after = crud.get_user(chat_id)
            current_repetitions_after = user_after[3] if user_after else current_repetitions_before
            
            # Если обновление не произошло, повторяем через crud
            if current_repetitions_after == current_repetitions_before:
                logger.warning(f"Первая попытка обновления не сработала, пробуем через crud")
                crud.update_user_notifications(chat_id, value)
                user_after = crud.get_user(chat_id)
                current_repetitions_after = user_after[3] if user_after else current_repetitions_before
            
            logger.info(f"Значение notifications обновлено: {current_repetitions_before} -> {current_repetitions_after}")
            
            # Сбрасываем кэш и состояние
            reset_daily_words_cache(chat_id)
            del pending_settings[chat_id]
            
            # Получаем текущие настройки для отображения
            current_words = user_after[2] if user_after else 5
            
            # Отправляем подтверждение
            await message.answer(
                f"✅ Настройки успешно обновлены!\n\n"
                f"📊 Количество слов в день: *{current_words}*\n"
                f"🔄 Количество повторений: *{current_repetitions_after}*",
                parse_mode="Markdown",
                reply_markup=notification_settings_menu_keyboard()
            )
        except Exception as e:
            logger.error(f"Ошибка при обновлении количества повторений: {e}")
            await message.answer(
                "❌ Произошла ошибка при обновлении настроек.",
                reply_markup=notification_settings_menu_keyboard()
            )
        
        return True
    
    return False

async def update_word_and_repetition_settings(chat_id, words_per_day, repetitions_per_word):
    """Обновляет количество слов и повторений для пользователя в базе данных."""
    try:
        # Обновляем параметры в базе данных
        crud.update_user_words_and_repetitions(chat_id, words_per_day, repetitions_per_word)
        logger.info(f"User {chat_id}: updated words per day to {words_per_day} and repetitions to {repetitions_per_word}")
    except Exception as e:
        logger.error(f"Error updating user {chat_id} settings: {e}")

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
    Полностью переписан для решения проблем с уведомлениями.
    """
    chat_id = callback.from_user.id
    try:
        data_parts = callback.data.split(":", 1)
        if len(data_parts) != 2:
            await callback.answer("Неверный формат данных.", show_alert=True)
            return
        
        _, option = data_parts
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

    # В функции process_settings_choice_callback заменить обработку options "words" и "repetitions":

    elif option == "words":
        # Получаем текущее значение из базы данных
        user = crud.get_user(chat_id)
        current_words = user[2] if user else 5
        current_repetitions = user[3] if user else 3
        
        await callback.message.edit_text(
            f"📊 *Количество слов в день*\n\n"
            f"Текущие настройки:\n"
            f"• Количество слов: *{current_words}*\n"
            f"• Количество повторений: *{current_repetitions}*\n\n"
            f"Выберите оптимальное количество новых слов для изучения ежедневно. "
            f"Рекомендуется от 5 до 15 слов для эффективного обучения.",
            parse_mode="Markdown",
            reply_markup=words_count_keyboard()
        )

    elif option == "repetitions":
        # Получаем текущее значение из базы данных
        user = crud.get_user(chat_id)
        current_words = user[2] if user else 5
        current_repetitions = user[3] if user else 3
        
        await callback.message.edit_text(
            f"🔄 *Количество повторений*\n\n"
            f"Текущие настройки:\n"
            f"• Количество слов: *{current_words}*\n"
            f"• Количество повторений: *{current_repetitions}*\n\n"
            f"Выберите, сколько раз вы хотите повторять каждое слово в течение дня. "
            f"Повторение помогает лучше запомнить слова.",
            parse_mode="Markdown",
            reply_markup=repetitions_count_keyboard()
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

def words_count_keyboard():
    """Создает клавиатуру с кнопками от 1 до 20 для выбора количества слов."""
    keyboard = InlineKeyboardMarkup(row_width=5)
    
    # Первая строка: 1-5
    row1 = [InlineKeyboardButton(str(i), callback_data=f"set_words:{i}") for i in range(1, 6)]
    keyboard.row(*row1)
    
    # Вторая строка: 6-10
    row2 = [InlineKeyboardButton(str(i), callback_data=f"set_words:{i}") for i in range(6, 11)]
    keyboard.row(*row2)
    
    # Третья строка: 11-15
    row3 = [InlineKeyboardButton(str(i), callback_data=f"set_words:{i}") for i in range(11, 16)]
    keyboard.row(*row3)
    
    # Четвертая строка: 16-20
    row4 = [InlineKeyboardButton(str(i), callback_data=f"set_words:{i}") for i in range(16, 21)]
    keyboard.row(*row4)
    
    # Кнопка "Назад"
    keyboard.row(InlineKeyboardButton("🔙 Назад", callback_data="settings:notifications"))
    
    return keyboard

def repetitions_count_keyboard():
    """Создает клавиатуру с кнопками от 1 до 5 для выбора количества повторений."""
    keyboard = InlineKeyboardMarkup(row_width=5)
    
    # Одна строка с кнопками 1-5
    buttons = [InlineKeyboardButton(str(i), callback_data=f"set_repetitions:{i}") for i in range(1, 6)]
    keyboard.row(*buttons)
    
    # Кнопка "Назад"
    keyboard.row(InlineKeyboardButton("🔙 Назад", callback_data="settings:notifications"))
    
    return keyboard

async def handle_set_words_count(callback: types.CallbackQuery, bot: Bot):
    """Обработчик выбора количества слов в день."""
    chat_id = callback.from_user.id
    try:
        _, count_str = callback.data.split(":", 1)
        count = int(count_str)
        
        if not (1 <= count <= 20):
            await callback.answer("Ошибка: недопустимое количество слов", show_alert=True)
            return
        
        # Обновляем в базе данных
        try:
            # Получаем текущие настройки для сравнения
            user_before = crud.get_user(chat_id)
            
            # Обновляем количество слов
            crud.update_user_words_per_day(chat_id, count)
            
            # Сбрасываем кэш
            reset_daily_words_cache(chat_id)
            
            # Получаем обновленные настройки
            user_after = crud.get_user(chat_id)
            current_words = user_after[2] if user_after else count
            current_repetitions = user_after[3] if user_after else 3
            
            # Отправляем подтверждение
            await callback.message.edit_text(
                f"✅ Настройки успешно обновлены!\n\n"
                f"📊 Количество слов в день: *{current_words}*\n"
                f"🔄 Количество повторений: *{current_repetitions}*",
                parse_mode="Markdown",
                reply_markup=notification_settings_menu_keyboard()
            )
            
            logger.info(f"Обновлено количество слов для пользователя {chat_id}: {count}")
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении количества слов: {e}")
            await callback.message.edit_text(
                "❌ Произошла ошибка при обновлении настроек.",
                reply_markup=notification_settings_menu_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка в обработчике выбора количества слов: {e}")
        await callback.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")
    
    await callback.answer()

async def handle_set_repetitions_count(callback: types.CallbackQuery, bot: Bot):
    """Обработчик выбора количества повторений."""
    chat_id = callback.from_user.id
    try:
        _, count_str = callback.data.split(":", 1)
        count = int(count_str)
        
        if not (1 <= count <= 5):
            await callback.answer("Ошибка: недопустимое количество повторений", show_alert=True)
            return
        
        # Обновляем в базе данных
        try:
            # Получаем текущие настройки для сравнения
            user_before = crud.get_user(chat_id)
            
            # Обновляем количество повторений
            crud.update_user_notifications(chat_id, count)
            
            # Сбрасываем кэш
            reset_daily_words_cache(chat_id)
            
            # Получаем обновленные настройки
            user_after = crud.get_user(chat_id)
            current_words = user_after[2] if user_after else 5
            current_repetitions = user_after[3] if user_after else count
            
            # Отправляем подтверждение
            await callback.message.edit_text(
                f"✅ Настройки успешно обновлены!\n\n"
                f"📊 Количество слов в день: *{current_words}*\n"
                f"🔄 Количество повторений: *{current_repetitions}*",
                parse_mode="Markdown",
                reply_markup=notification_settings_menu_keyboard()
            )
            
            logger.info(f"Обновлено количество повторений для пользователя {chat_id}: {count}")
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении количества повторений: {e}")
            await callback.message.edit_text(
                "❌ Произошла ошибка при обновлении настроек.",
                reply_markup=notification_settings_menu_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка в обработчике выбора количества повторений: {e}")
        await callback.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")
    
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
        
        # Prepare message with current set info
        message_text = f"Доступные сеты для уровня {user_level}:"
        if current_set:
            message_text = f"Текущий сет: *{current_set}*\n\n" + message_text
        
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        
        # Очищаем предыдущие записи в кэше для этого пользователя
        global set_index_cache
        for key in list(set_index_cache.keys()):
            if key.startswith(f"{chat_id}_"):
                del set_index_cache[key]
        
        # Ограничиваем длину callback_data, чтобы избежать ошибки Button_data_invalid
        for idx, filename in enumerate(set_files):
            set_name = os.path.splitext(filename)[0]
            
            # Используем индекс вместо имени сета в callback_data для предотвращения ошибки
            set_index = idx + 1  # Начинаем с 1
            
            # Всегда показываем подтверждение при смене сета, если текущий сет задан
            callback_data = f"confirm_idx:{set_index}" if current_set and current_set != set_name else f"set_idx:{set_index}"
            
            # Сохраняем имя сета в глобальный cache для восстановления по индексу
            set_index_cache[f"{chat_id}_{set_index}"] = set_name
            
            keyboard.add(types.InlineKeyboardButton(set_name, callback_data=callback_data))
        
        keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="menu:settings"))
        
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
        
        # Получаем имя сета из глобального кэша
        global set_index_cache
        set_name = set_index_cache.get(f"{chat_id}_{set_index}")
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
        
        # Если это смена сета - всегда показываем подтверждение
        if is_change:
            # Отправляем запрос на подтверждение
            await handle_confirm_set_by_index(callback, bot)
        else:
            # Если это первый выбор сета, просто устанавливаем его
            crud.update_user_chosen_set(chat_id, set_name)
            user_set_selection[chat_id] = set_name
            reset_daily_words_cache(chat_id)
            
            # Читаем содержимое сета для отображения
            set_path = os.path.join(LEVELS_DIR, user_level, f"{set_name}.txt")
            content = ""
            try:
                with open(set_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                try:
                    with open(set_path, "r", encoding="cp1251") as f:
                        content = f.read()
                except Exception as e:
                    logger.error(f"Ошибка при чтении файла с альтернативной кодировкой: {e}")
                    content = "Ошибка при чтении содержимого сета."
            except Exception as e:
                logger.error(f"Ошибка при чтении файла сета: {e}")
                content = "Ошибка при чтении содержимого сета."
            
            # Форматируем сообщение с содержимым сета
            intro_text = f"✅ Выбран сет '{set_name}' для уровня {user_level}.\nСлова сета:\n\n"
            
            # Ограничиваем длину сообщения
            MAX_MESSAGE_LENGTH = 3800
            if len(intro_text) + len(content) > MAX_MESSAGE_LENGTH:
                lines = content.split('\n')
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
            
            # Отправляем сообщение с информацией о выбранном сете
            await callback.message.edit_text(
                message_text,
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
        
        # Получаем имя сета из глобального кэша
        global set_index_cache
        set_name = set_index_cache.get(f"{chat_id}_{set_index}")
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
        
        # Читаем содержимое выбранного сета
        user_level = user[1]
        set_path = os.path.join(LEVELS_DIR, user_level, f"{set_name}.txt")
        content = ""
        
        try:
            with open(set_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(set_path, "r", encoding="cp1251") as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Ошибка при чтении файла с альтернативной кодировкой: {e}")
                content = "Ошибка при чтении содержимого сета."
        except Exception as e:
            logger.error(f"Ошибка при чтении файла сета: {e}")
            content = "Ошибка при чтении содержимого сета."
            
        # Форматируем сообщение для предварительного просмотра сета
        intro_text = f"ℹ️ *Предварительный просмотр сета '{set_name}'*\n\n"
        
        # Ограничиваем длину предварительного просмотра
        MAX_PREVIEW_LENGTH = 1500
        
        if len(content) > MAX_PREVIEW_LENGTH:
            lines = content.split('\n')
            preview_content = ""
            preview_line_count = 0
            word_count = len(lines)
            
            for line in lines:
                if len(preview_content) + len(line) < MAX_PREVIEW_LENGTH:
                    preview_content += line + "\n"
                    preview_line_count += 1
                else:
                    break
                    
            preview_text = preview_content + f"\n...и еще {word_count - preview_line_count} слов(а)."
        else:
            preview_text = content
            
        # Создаем клавиатуру для подтверждения
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton("✅ Да, сменить", callback_data=f"set_chg_idx:{set_index}"),
            types.InlineKeyboardButton("❌ Нет, отмена", callback_data="set_change_cancel")
        )
        
        # Отправляем сообщение с предупреждением и предварительным просмотром сета
        message = (
            f"⚠️ *Внимание! Смена сета приведет к полному сбросу прогресса.*\n\n"
            f"Текущий сет: *{current_set}*\n"
            f"Новый сет: *{set_name}*\n\n"
            f"При смене сета ваш словарь будет полностью очищен. Вы уверены?\n\n"
            f"Содержимое нового сета:\n\n{preview_text}"
        )
        
        await callback.message.edit_text(
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except ValueError:
        await callback.answer("Неверный формат данных.")
    except Exception as e:
        logger.error(f"Ошибка при подтверждении смены сета: {e}")
        await callback.answer("Произошла ошибка при подготовке подтверждения.")

async def handle_set_change_confirmed_by_index(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик подтверждения смены сета по индексу.
    """
    chat_id = callback.from_user.id
    try:
        _, set_index = callback.data.split(":", 1)
        set_index = int(set_index)
        
        # Получаем имя сета из глобального кэша
        global set_index_cache
        set_name = set_index_cache.get(f"{chat_id}_{set_index}")
        if not set_name:
            await callback.answer("Ошибка: информация о сете не найдена. Пожалуйста, попробуйте снова.")
            return
        
        # Очищаем словарь пользователя
        try:
            crud.clear_learned_words_for_user(chat_id)
            logger.info(f"Dictionary cleared for user {chat_id} due to set change by index")
        except Exception as e:
            logger.error(f"Error clearing dictionary: {e}")
            await bot.send_message(chat_id, "Произошла ошибка при очистке словаря. Пожалуйста, попробуйте позже.")
            await callback.answer()
            return
        
        # Получаем уровень пользователя
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
        
        # Обновляем выбранный сет
        crud.update_user_chosen_set(chat_id, set_name)
        user_set_selection[chat_id] = set_name
        reset_daily_words_cache(chat_id)
        
        # Отправляем стикер
        sticker_id = get_congratulation_sticker()
        if sticker_id:
            await bot.send_sticker(chat_id, sticker_id)
        
        # Читаем содержимое сета
        content = ""
        try:
            with open(set_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(set_path, "r", encoding="cp1251") as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Ошибка при чтении файла с альтернативной кодировкой: {e}")
                content = "Ошибка при чтении содержимого сета."
        except Exception as e:
            logger.error(f"Ошибка при чтении файла сета: {e}")
            content = "Ошибка при чтении содержимого сета."
        
        # Форматируем сообщение с учетом ограничений Telegram
        intro_text = f"✅ Выбран сет '{set_name}' для уровня {user_level}.\n⚠️ Словарь успешно очищен.\nСлова сета:\n\n"
        
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
        logger.error(f"Error in handle_set_change_confirmed_by_index: {e}")
        await bot.send_message(chat_id, f"Произошла ошибка при смене сета: {str(e)}. Пожалуйста, попробуйте позже.")
    
    await callback.answer()

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
    
    # Сохраняем текущий уровень для сравнения
    current_level = user[1]
    
    # Проверяем текущий сет пользователя
    current_set = None
    if chat_id in user_set_selection:
        current_set = user_set_selection[chat_id]
    
    # Если нет в кэше, смотрим в базе данных
    if not current_set and len(user) > 6 and user[6]:
        current_set = user[6]
    
    # Обновляем уровень пользователя
    crud.update_user_level(chat_id, level)
    
    # Важно: мы НЕ меняем выбранный сет при смене уровня
    # Сет будет меняться только при явном выборе пользователем в разделе "Выбор сета"
    
    # Сбрасываем кэш ежедневных слов для обновления состояния
    reset_daily_words_cache(chat_id)
    
    # Формируем сообщение для пользователя
    if current_level != level:
        message = f"Уровень изменен с {current_level} на {level}."
        if current_set:
            message += f"\nТекущий набор слов: {current_set}"
            
            # Проверяем, существует ли файл сета в новом уровне (для информации)
            set_file_path = os.path.join(LEVELS_DIR, level, f"{current_set}.txt")
            set_exists = os.path.exists(set_file_path)
            
            # Если файл не существует в новом уровне, предупреждаем пользователя
            if not set_exists:
                # Проверяем с учетом возможного различия в регистре
                try:
                    level_dir = os.path.join(LEVELS_DIR, level)
                    if os.path.exists(level_dir):
                        for file in os.listdir(level_dir):
                            if file.lower() == f"{current_set}.txt".lower():
                                set_exists = True
                                break
                except Exception as e:
                    logger.error(f"Ошибка при проверке существования файла сета: {e}")
                
                if not set_exists:
                    message += f"\n\n⚠️ Обратите внимание: выбранный набор '{current_set}' не найден для уровня {level}. Это может привести к ошибкам. Рекомендуется выбрать набор из текущего уровня в разделе 'Выбор сета'."
    else:
        message = f"Уровень установлен на {level}."
        if current_set:
            message += f"\nТекущий набор слов: {current_set}"
    
    await bot.send_message(chat_id, message, reply_markup=settings_menu_keyboard())
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
    await bot.send_message(chat_id, f"Часовой пояс установлен на {tz}.", reply_markup=settings_menu_keyboard())
    await callback.answer()

async def process_text_setting(message: types.Message, bot: Bot = None):
    """Обработчик ввода числа для настроек (слов или повторений)"""
    chat_id = message.chat.id
    text = message.text.strip()
    
    # Проверяем, находится ли пользователь в режиме ожидания ввода
    if chat_id not in pending_settings:
        # Не наш случай, позволяем другим обработчикам обработать сообщение
        return False
    
    logger.info(f"Получен ввод от пользователя {chat_id}: '{text}', режим: {pending_settings[chat_id]}")
    
    # Проверяем, что введено число
    if not text.isdigit():
        await message.answer(
            "⚠️ Ошибка: введите корректное число.",
            reply_markup=notification_settings_menu_keyboard()
        )
        return True
    
    value = int(text)
    setting_type = pending_settings[chat_id]
    
    # Обработка настройки количества слов
    if setting_type == "words":
        if not (1 <= value <= 20):
            await message.answer(
                "⚠️ Ошибка: число должно быть от 1 до 20.",
                reply_markup=notification_settings_menu_keyboard()
            )
            return True
        
        try:
            # Обновляем в базе данных
            before_update = crud.get_user(chat_id)
            
            # Используем правильный метод обновления
            crud.update_user_words_per_day(chat_id, value)
            logger.info(f"Обновлено количество слов для пользователя {chat_id}: {value}")
            
            # Сбрасываем кэш
            from utils.helpers import reset_daily_words_cache
            reset_daily_words_cache(chat_id)
            
            # Удаляем из словаря ожидания
            del pending_settings[chat_id]
            
            # Получаем обновленные данные для отображения
            after_update = crud.get_user(chat_id)
            current_words = after_update[2] if after_update else value
            current_repetitions = after_update[3] if after_update else 3
            
            # Отправляем подтверждение с текущими настройками
            await message.answer(
                f"✅ Настройки обновлены!\n\n"
                f"📊 Количество слов в день: *{current_words}*\n"
                f"🔄 Количество повторений: *{current_repetitions}*",
                parse_mode="Markdown",
                reply_markup=notification_settings_menu_keyboard()
            )
        except Exception as e:
            logger.error(f"Ошибка при обновлении количества слов: {e}")
            await message.answer(
                "❌ Произошла ошибка при обновлении настроек.",
                reply_markup=notification_settings_menu_keyboard()
            )
        
        return True
    
    # Обработка настройки количества повторений
    elif setting_type == "repetitions":
        if not (1 <= value <= 5):
            await message.answer(
                "⚠️ Ошибка: число должно быть от 1 до 5.",
                reply_markup=notification_settings_menu_keyboard()
            )
            return True
        
        try:
            # Обновляем в базе данных
            before_update = crud.get_user(chat_id)
            
            # Используем правильный метод обновления
            crud.update_user_notifications(chat_id, value)
            logger.info(f"Обновлено количество повторений для пользователя {chat_id}: {value}")
            
            # Сбрасываем кэш
            from utils.helpers import reset_daily_words_cache
            reset_daily_words_cache(chat_id)
            
            # Удаляем из словаря ожидания
            del pending_settings[chat_id]
            
            # Получаем обновленные данные для отображения
            after_update = crud.get_user(chat_id)
            current_words = after_update[2] if after_update else 5
            current_repetitions = after_update[3] if after_update else value
            
            # Отправляем подтверждение с текущими настройками
            await message.answer(
                f"✅ Настройки обновлены!\n\n"
                f"📊 Количество слов в день: *{current_words}*\n"
                f"🔄 Количество повторений: *{current_repetitions}*",
                parse_mode="Markdown",
                reply_markup=notification_settings_menu_keyboard()
            )
        except Exception as e:
            logger.error(f"Ошибка при обновлении количества повторений: {e}")
            await message.answer(
                "❌ Произошла ошибка при обновлении настроек.",
                reply_markup=notification_settings_menu_keyboard()
            )
        
        return True
    
    return False  # если тип настройки не распознан

async def process_notification_back(callback: types.CallbackQuery, bot: Bot):
    """Обработчик возврата из меню уведомлений в меню настроек"""
    await callback.message.edit_text("Настройки бота:", reply_markup=settings_menu_keyboard())
    await callback.answer()

def register_settings_handlers(dp: Dispatcher, bot: Bot):
    """Register all settings handlers"""
    # ВАЖНО: Регистрируем обработчик текстовых сообщений ПЕРВЫМ
    # с более простым условием для гарантированной обработки
    dp.register_message_handler(
        partial(process_settings_input, bot=bot),
        lambda message: bool(message.text) and message.chat.id in pending_settings,
        state="*",
        content_types=['text']
    )
    # Регистрируем обработчики для кнопок выбора количества слов и повторений
    dp.register_callback_query_handler(
        partial(handle_set_words_count, bot=bot),
        lambda c: c.data and c.data.startswith("set_words:")
    )
    
    dp.register_callback_query_handler(
        partial(handle_set_repetitions_count, bot=bot),
        lambda c: c.data and c.data.startswith("set_repetitions:")
    )
    # Basic settings handlers
    dp.register_callback_query_handler(
        partial(show_settings_callback, bot=bot),
        lambda c: c.data == "menu:settings"
    )
    dp.register_callback_query_handler(
        partial(process_notification_back, bot=bot),
        lambda c: c.data == "settings:back" or c.data == "notifications:back"
    )
    
    # Регистрируем обработчики для настроек и их подменю
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
    
    # Обработчики для выбора сета по индексу
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

async def process_settings_mysettings(callback: types.CallbackQuery, bot: Bot):
    """
    Displays user settings with improved formatting and statistics.
    Handles edge cases better and creates a more visually appealing display.
    """
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
        return
    
    # Check and set default set if missing
    current_set = None
    
    # Check set in cache
    if chat_id in user_set_selection:
        current_set = user_set_selection[chat_id]
    
    # If not in cache, check database
    if not current_set and len(user) > 6 and user[6]:
        current_set = user[6]
    
    # If still not set, use default for level
    if not current_set:
        level = user[1]
        default_set = DEFAULT_SETS.get(level)
        if default_set:
            try:
                crud.update_user_chosen_set(chat_id, default_set)
                user_set_selection[chat_id] = default_set
                current_set = default_set
                logger.info(f"Set default set {default_set} for user {chat_id} during profile view")
            except Exception as e:
                logger.error(f"Error setting default set for user {chat_id}: {e}")
    
    # Create user settings dictionary
    user_settings = {
        "level": user[1],
        "words_per_day": user[2],
        "repetitions": user[3],
        "timezone": user[5] if len(user) > 5 and user[5] else "Не задан",
        "chosen_set": current_set or "Не выбран",
        "test_words_count": user[7] if len(user) > 7 and user[7] else 5,
        "memorize_words_count": user[8] if len(user) > 8 and user[8] else 5
    }
    
    # Format with nice formatting
    message = "👤 *Ваш профиль*\n\n"
    message += f"🔤 *Уровень:* {user_settings['level']}\n"
    message += f"📊 *Слов в день:* {user_settings['words_per_day']}\n"
    message += f"🔄 *Повторений:* {user_settings['repetitions']}\n"
    message += f"🌐 *Часовой пояс:* {user_settings['timezone']}\n"
    message += f"📚 *Выбранный набор:* {user_settings['chosen_set']}\n"
    message += f"📝 *Слов в тесте:* {user_settings['test_words_count']}\n"
    message += f"📖 *Слов в заучивании:* {user_settings['memorize_words_count']}\n\n"
    
    # Add statistics
    try:
        # Get learned words
        learned_words = crud.get_learned_words(chat_id)
        total_learned = len(learned_words)
        
        message += f"📈 *Статистика*\n"
        message += f"📝 Выучено слов: {total_learned}\n"
        
        # If there's a chosen set, count words in it
        if current_set:
            level = user_settings['level']
            set_path = os.path.join(LEVELS_DIR, level, f"{current_set}.txt")
            
            if os.path.exists(set_path):
                try:
                    # Try different encodings
                    encodings = ['utf-8', 'cp1251']
                    set_words = []
                    
                    for encoding in encodings:
                        try:
                            with open(set_path, 'r', encoding=encoding) as f:
                                set_words = [line.strip() for line in f if line.strip()]
                            if set_words:
                                break
                        except UnicodeDecodeError:
                            continue
                    
                    if set_words:
                        total_set_words = len(set_words)
                        
                        # Create set of learned English words
                        learned_english_words = set(extract_english(word[0]).lower() for word in learned_words)
                        
                        # Count words from set that are learned
                        learned_from_set = 0
                        for word in set_words:
                            english_part = extract_english(word).lower()
                            if english_part in learned_english_words:
                                learned_from_set += 1
                        
                        # Add progress info
                        progress_percent = learned_from_set / total_set_words * 100 if total_set_words > 0 else 0
                        progress_bar = format_progress_bar(learned_from_set, total_set_words, 10)
                        message += f"📊 Прогресс в текущем сете: {learned_from_set}/{total_set_words} ({progress_percent:.1f}%)\n"
                        message += f"{progress_bar}\n"
                except Exception as e:
                    logger.error(f"Error calculating set statistics: {e}")
            
            # Find completed sets
            level_dir = os.path.join(LEVELS_DIR, level)
            if os.path.exists(level_dir):
                try:
                    set_files = [f[:-4] for f in os.listdir(level_dir) if f.endswith('.txt')]
                    completed_sets = []
                    
                    for set_name in set_files:
                        set_path = os.path.join(level_dir, f"{set_name}.txt")
                        if os.path.exists(set_path):
                            try:
                                # Try different encodings
                                for encoding in encodings:
                                    try:
                                        with open(set_path, 'r', encoding=encoding) as f:
                                            set_words = [line.strip() for line in f if line.strip()]
                                        if set_words:
                                            break
                                    except UnicodeDecodeError:
                                        continue
                                
                                if set_words:
                                    # Check if all words are learned
                                    learned_english_words = set(extract_english(word[0]).lower() for word in learned_words)
                                    all_learned = True
                                    
                                    for word in set_words:
                                        english_part = extract_english(word).lower()
                                        if english_part not in learned_english_words:
                                            all_learned = False
                                            break
                                    
                                    if all_learned:
                                        completed_sets.append(set_name)
                            except Exception as e:
                                logger.error(f"Error checking set {set_name}: {e}")
                    
                    # Add completed sets info
                    if completed_sets:
                        message += f"\n🎓 *Выученные сеты ({len(completed_sets)})* 🎓\n"
                        for set_name in completed_sets[:5]:  # Limit to 5 to avoid message too long
                            message += f"✅ {set_name}\n"
                        if len(completed_sets) > 5:
                            message += f"...и еще {len(completed_sets)-5} сетов\n"
                    else:
                        message += "\nНет полностью выученных сетов.\n"
                except Exception as e:
                    logger.error(f"Error getting completed sets: {e}")
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        message += "Ошибка при получении статистики.\n"
    
    # Send the formatted message
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