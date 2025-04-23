
# Основные импорты должны быть в начале файла
import random
from aiogram import types, Dispatcher, Bot
from keyboards.submenus import learning_menu_keyboard, learning_settings_keyboard
from keyboards.main_menu import main_menu_keyboard
from utils.helpers import load_words_for_set, extract_english
from utils.quiz_helpers import load_quiz_data
from database import crud
from database.db import db_manager
from functools import partial
import logging
import os
from config import LEVELS_DIR

logger = logging.getLogger(__name__)

# Глобальный словарь для хранения состояния ввода
pending_learning_settings = {}

# Глобальный словарь для хранения состояния тестов (как в quiz.py)
learning_test_states = {}

# Добавить в начало файла handlers/learning.py:

# Константы для доступа к полям пользователя
USER_LEVEL = 1
USER_WORDS_PER_DAY = 2
USER_REPETITIONS = 3
USER_REMINDER_TIME = 4
USER_TIMEZONE = 5
USER_CHOSEN_SET = 6
USER_TEST_WORDS_COUNT = 7
USER_MEMORIZE_WORDS_COUNT = 8

def test_words_count_keyboard():
    """Создает клавиатуру с кнопками от 1 до 20 для выбора количества слов в тесте."""
    keyboard = types.InlineKeyboardMarkup(row_width=5)
    
    # Первая строка: 1-5
    row1 = [types.InlineKeyboardButton(str(i), callback_data=f"learn:test_count:{i}") for i in range(1, 6)]
    keyboard.row(*row1)
    
    # Вторая строка: 6-10
    row2 = [types.InlineKeyboardButton(str(i), callback_data=f"learn:test_count:{i}") for i in range(6, 11)]
    keyboard.row(*row2)
    
    # Третья строка: 11-15
    row3 = [types.InlineKeyboardButton(str(i), callback_data=f"learn:test_count:{i}") for i in range(11, 16)]
    keyboard.row(*row3)
    
    # Четвертая строка: 16-20
    row4 = [types.InlineKeyboardButton(str(i), callback_data=f"learn:test_count:{i}") for i in range(16, 21)]
    keyboard.row(*row4)
    
    # Кнопка "Назад"
    keyboard.row(types.InlineKeyboardButton("🔙 Назад", callback_data="learning:settings"))
    
    return keyboard

def memorize_words_count_keyboard():
    """Создает клавиатуру с кнопками от 1 до 20 для выбора количества слов для заучивания."""
    keyboard = types.InlineKeyboardMarkup(row_width=5)
    
    # Первая строка: 1-5
    row1 = [types.InlineKeyboardButton(str(i), callback_data=f"learn:memorize_count:{i}") for i in range(1, 6)]
    keyboard.row(*row1)
    
    # Вторая строка: 6-10
    row2 = [types.InlineKeyboardButton(str(i), callback_data=f"learn:memorize_count:{i}") for i in range(6, 11)]
    keyboard.row(*row2)
    
    # Третья строка: 11-15
    row3 = [types.InlineKeyboardButton(str(i), callback_data=f"learn:memorize_count:{i}") for i in range(11, 16)]
    keyboard.row(*row3)
    
    # Четвертая строка: 16-20
    row4 = [types.InlineKeyboardButton(str(i), callback_data=f"learn:memorize_count:{i}") for i in range(16, 21)]
    keyboard.row(*row4)
    
    # Кнопка "Назад"
    keyboard.row(types.InlineKeyboardButton("🔙 Назад", callback_data="learning:settings"))
    
    return keyboard

# Безопасное получение настроек пользователя с учетом возможных изменений в структуре
def get_user_setting(user, index, default_value):
    """Безопасно извлекает настройку пользователя с указанным индексом"""
    try:
        if user and len(user) > index and user[index] is not None:
            return user[index]
    except Exception as e:
        logger.error(f"Ошибка при получении настройки с индексом {index}: {e}")
    return default_value

# Затем изменить функцию handle_dictionary_test:

async def handle_dictionary_test(callback: types.CallbackQuery, bot: Bot):
    """Обработчик запуска теста по словарю"""
    chat_id = callback.from_user.id
    user = crud.get_user(chat_id)
    if not user:
        await callback.answer("Профиль не найден. Используйте /start.", show_alert=True)
        return
    
    # Получаем словарь пользователя
    learned_words = crud.get_learned_words(chat_id)
    if not learned_words:
        await callback.message.edit_text(
            "📚 *Ваш словарь пуст*\n\n"
            "Пройдите квизы, чтобы добавить слова в свой словарь!",
            parse_mode="Markdown",
            reply_markup=learning_menu_keyboard()
        )
        await callback.answer()
        return
    
    # Получаем настроенное количество слов для теста
    # Получаем настроенное количество слов для теста
    test_words_count = 5  # Значение по умолчанию
    try:
        if len(user) > 7 and user[7] is not None:
            test_words_count = int(user[7])
            logger.info(f"Получено значение test_words_count из базы: {test_words_count}")
        else:
            logger.warning(f"Не удалось получить test_words_count из кортежа пользователя длиной {len(user)}")
            # Прямой запрос к базе данных
            with db_manager.get_cursor() as cursor:
                cursor.execute("SELECT test_words_count FROM users WHERE chat_id = ?", (chat_id,))
                result = cursor.fetchone()
                if result and result[0]:
                    test_words_count = int(result[0])
                    logger.info(f"Получено значение test_words_count прямым запросом: {test_words_count}")
    except Exception as e:
        logger.error(f"Ошибка при получении test_words_count: {e}")
        
    logger.info(f"Пользователь {chat_id} запускает тест по словарю с {test_words_count} словами")
    
    # Проверяем, хватает ли слов в словаре
    if test_words_count > len(learned_words):
        logger.info(f"В словаре пользователя {chat_id} меньше слов ({len(learned_words)}), чем запрошено ({test_words_count})")
        test_words_count = len(learned_words)
    
    # Выбираем случайные слова из словаря
    selected_words = random.sample(learned_words, test_words_count)
    
    # Получаем данные для квиза из текущего уровня
    level = get_user_setting(user, USER_LEVEL, "A1")
    chosen_set = get_user_setting(user, USER_CHOSEN_SET, None)
    
    # Загружаем все данные для квиза
    quiz_data = load_quiz_data(level, chosen_set)
    if not quiz_data:
        await callback.message.edit_text(
            f"⚠️ Ошибка: не удалось загрузить данные квиза для уровня {level}.",
            parse_mode="Markdown",
            reply_markup=learning_menu_keyboard()
        )
        await callback.answer()
        return
    
    # Создаем словарь соответствия английских слов и их переводов
    translations = {item["word"].lower(): item["translation"] for item in quiz_data}
    
    # Создаем вопросы для теста
    questions = []
    for word, translation in selected_words:
        english_word = extract_english(word).lower()
        correct_translation = translation
        
        # Получаем варианты ответов (исключая правильный)
        options = [correct_translation]
        all_translations = list(translations.values())
        
        # Исключаем правильный ответ из пула дистракторов
        if correct_translation in all_translations:
            all_translations.remove(correct_translation)
        
        # Добавляем дистракторы
        if len(all_translations) >= 3:
            options.extend(random.sample(all_translations, 3))
        else:
            options.extend(random.choices(all_translations, k=3) if all_translations else ["???", "???", "???"])
        
        # Перемешиваем варианты ответов
        random.shuffle(options)
        
        correct_index = options.index(correct_translation)
        
        questions.append({
            "word": word,
            "correct": correct_translation,
            "options": options,
            "correct_index": correct_index,
            "is_revision": True,  # Это тест по словарю, режим проверки
            "test_type": "dictionary"  # Указываем тип теста для логики обработки ответов
        })
    
    # Сохраняем состояние теста
    learning_test_states[chat_id] = {
        "questions": questions,
        "current_index": 0,
        "correct": 0,
        "is_revision": True,
        "test_type": "dictionary"
    }
    
    # Начинаем тест
    await callback.answer()
    await send_learning_test_question(chat_id, bot)

# Проверяем и добавляем колонки для настроек обучения
def ensure_learning_columns():
    """Проверяет и добавляет колонки для настроек обучения"""
    try:
        from database.db import db_manager
        with db_manager.get_cursor() as cursor:
            # Проверяем структуру таблицы
            cursor.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Добавляем колонки, если их нет
            if 'test_words_count' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN test_words_count INTEGER DEFAULT 5")
                
            if 'memorize_words_count' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN memorize_words_count INTEGER DEFAULT 5")
                
            # Комитим изменения
            db_manager.conn.commit()
            
        logger.info("Колонки для настроек обучения проверены")
    except Exception as e:
        logger.error(f"Ошибка при проверке колонок: {e}")

# Вызывается при импорте модуля
ensure_learning_columns()

async def handle_memorize_set(callback: types.CallbackQuery, bot: Bot):
    """Обработчик запуска заучивания сета"""
    chat_id = callback.from_user.id
    
    # Получаем информацию о пользователе
    user = crud.get_user(chat_id)
    if not user:
        await callback.answer("Профиль не найден. Используйте /start.", show_alert=True)
        return
    
    # Получаем уровень и выбранный сет
    level = user[1]
    
    # Ищем сет в базе данных
    chosen_set = None
    if len(user) > 6 and user[6]:
        chosen_set = user[6]
        logger.info(f"Получен сет '{chosen_set}' из базы данных для пользователя {chat_id}")
    
    # Если сет не найден в базе данных, проверяем его в кэше
    if not chosen_set:
        try:
            from handlers.settings import user_set_selection
            chosen_set = user_set_selection.get(chat_id)
            logger.info(f"Получен сет '{chosen_set}' из кэша для пользователя {chat_id}")
        except ImportError:
            logger.error("Ошибка импорта user_set_selection, используем набор по умолчанию")
    
    # Если сет все еще не найден, устанавливаем стандартный
    if not chosen_set:
        from config import DEFAULT_SETS
        chosen_set = DEFAULT_SETS.get(level)
        if chosen_set:
            # Обновляем базу данных и кэш
            crud.update_user_chosen_set(chat_id, chosen_set)
            try:
                from handlers.settings import user_set_selection
                user_set_selection[chat_id] = chosen_set
            except ImportError:
                logger.error("Ошибка импорта user_set_selection для обновления кэша")
            logger.info(f"Установлен стандартный сет '{chosen_set}' для пользователя {chat_id}")
        else:
            await callback.message.edit_text(
                f"⚠️ Ошибка: не найден стандартный сет для уровня {level}.",
                parse_mode="Markdown",
                reply_markup=learning_menu_keyboard()
            )
            await callback.answer()
            return
    
    # Проверяем наличие файла сета
    set_file_path = os.path.join(LEVELS_DIR, level, f"{chosen_set}.txt")
    
    if not os.path.exists(set_file_path):
        # Пробуем найти файл с другим регистром
        found = False
        try:
            parent_dir = os.path.dirname(set_file_path)
            if os.path.exists(parent_dir):
                for file in os.listdir(parent_dir):
                    if file.lower() == f"{chosen_set}.txt".lower():
                        set_file_path = os.path.join(parent_dir, file)
                        found = True
                        break
        except Exception as e:
            logger.error(f"Ошибка при поиске файла с другим регистром: {e}")
        
        if not found:
            await callback.message.edit_text(
                f"⚠️ Ошибка: не найден файл для сета '{chosen_set}' уровня {level}.\n"
                f"Пожалуйста, выберите другой сет в настройках.",
                parse_mode="Markdown",
                reply_markup=learning_menu_keyboard()
            )
            await callback.answer()
            return
    
    # Загружаем слова из сета с улучшенной обработкой ошибок
    set_words = []
    try:
        encodings = ['utf-8', 'cp1251', 'latin-1', 'iso-8859-1']  # Расширенный список кодировок
        for encoding in encodings:
            try:
                with open(set_file_path, 'r', encoding=encoding) as f:
                    set_words = [line.strip() for line in f if line.strip()]
                if set_words:  # Если удалось прочитать слова, выходим из цикла
                    logger.info(f"Файл успешно прочитан с кодировкой {encoding}")
                    break
            except UnicodeDecodeError:
                continue  # Пробуем следующую кодировку
            except Exception as e:
                logger.error(f"Ошибка при чтении файла с кодировкой {encoding}: {e}")
                break
        
        if not set_words:
            logger.error(f"Не удалось прочитать файл сета ни с одной кодировкой: {set_file_path}")
            await callback.message.edit_text(
                f"⚠️ Ошибка при чтении файла сета. Пожалуйста, обратитесь к администратору.",
                parse_mode="Markdown",
                reply_markup=learning_menu_keyboard()
            )
            await callback.answer()
            return
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при чтении файла сета {set_file_path}: {e}")
        await callback.message.edit_text(
            f"⚠️ Непредвиденная ошибка при чтении файла сета.",
            parse_mode="Markdown",
            reply_markup=learning_menu_keyboard()
        )
        await callback.answer()
        return
    
    if not set_words:
        await callback.message.edit_text(
            f"⚠️ Сет '{chosen_set}' не содержит слов.",
            parse_mode="Markdown",
            reply_markup=learning_menu_keyboard()
        )
        await callback.answer()
        return
    
    # Получаем количество слов для заучивания из настроек пользователя
    # Используем безопасное получение данных с проверкой длины кортежа
    memorize_words_count = 5  # Значение по умолчанию
    try:
        if len(user) > 8 and user[8] is not None:
            memorize_words_count = user[8]
        else:
            # Если значение отсутствует, пробуем получить его непосредственно из БД
            with db_manager.get_cursor() as cursor:
                cursor.execute("SELECT memorize_words_count FROM users WHERE chat_id = ?", (chat_id,))
                result = cursor.fetchone()
                if result and result[0] is not None:
                    memorize_words_count = result[0]
    except Exception as e:
        logger.error(f"Ошибка при получении memorize_words_count для пользователя {chat_id}: {e}")
    
    logger.info(f"Пользователь {chat_id} запускает заучивание сета с {memorize_words_count} словами")
    
    # Проверяем, не превышает ли запрошенное количество слов размер сета
    if memorize_words_count > len(set_words):
        logger.info(f"В сете '{chosen_set}' меньше слов ({len(set_words)}), чем запрошено ({memorize_words_count})")
        memorize_words_count = len(set_words)
    
    # Выбираем случайные слова из сета
    selected_words = random.sample(set_words, memorize_words_count)
    
    # Получаем уже выученные слова
    learned_raw = crud.get_learned_words(chat_id)
    learned_set = set(extract_english(item[0]).lower() for item in learned_raw)
    
    # Загружаем данные для квиза
    quiz_data = load_quiz_data(level, chosen_set)
    if not quiz_data:
        await callback.message.edit_text(
            f"⚠️ Ошибка: не удалось загрузить данные квиза для уровня {level}.",
            parse_mode="Markdown",
            reply_markup=learning_menu_keyboard()
        )
        await callback.answer()
        return
    
    # Создаем словарь соответствия английских слов и их переводов
    translations = {item["word"].lower(): item["translation"] for item in quiz_data}
    
    # Создаем вопросы для заучивания
    questions = []
    for word_line in selected_words:
        # Извлекаем только английское слово без перевода
        english_part = ""
        russian_part = ""
        
        # Проверяем различные форматы разделителей
        for separator in [" - ", " – ", ": "]:
            if separator in word_line:
                parts = word_line.split(separator, 1)
                english_part = parts[0].strip()
                russian_part = parts[1].strip() if len(parts) > 1 else ""
                break
        
        # Если разделителей не найдено, используем функцию extract_english
        if not english_part:
            english_part = extract_english(word_line)
        
        # Если не удалось выделить перевод, используем словарь переводов
        if not russian_part:
            russian_part = translations.get(english_part.lower(), english_part)
        
        # Определяем, является ли это повторением или изучением нового слова
        is_revision = english_part.lower() in learned_set
        
        # Получаем варианты ответов (исключая правильный)
        options = [russian_part]
        all_translations = list(translations.values())
        
        # Исключаем правильный ответ из пула дистракторов
        if russian_part in all_translations:
            all_translations.remove(russian_part)
        
        # Добавляем дистракторы
        if len(all_translations) >= 3:
            options.extend(random.sample(all_translations, 3))
        else:
            options.extend(random.choices(all_translations, k=3) if all_translations else ["???", "???", "???"])
        
        # Перемешиваем варианты ответов
        random.shuffle(options)
        
        correct_index = options.index(russian_part)
        
        questions.append({
            "word": english_part,  # Только английское слово
            "correct": russian_part,
            "options": options,
            "correct_index": correct_index,
            "is_revision": is_revision,
            "test_type": "memorize"  # Указываем тип теста для логики обработки ответов
        })
    
    # Сохраняем состояние теста
    learning_test_states[chat_id] = {
        "questions": questions,
        "current_index": 0,
        "correct": 0,
        "is_revision": False,  # Это заучивание, а не повторение
        "test_type": "memorize"
    }
    
    # Начинаем тест
    await callback.answer()
    await send_learning_test_question(chat_id, bot)

async def handle_learning_menu(callback: types.CallbackQuery, bot: Bot):
    """Отображает меню обучения"""
    # Проверяем наличие необходимых колонок
    
    await callback.message.edit_text("📚 Выберите режим обучения:", reply_markup=learning_menu_keyboard())
    await callback.answer()

async def handle_learning_settings(callback: types.CallbackQuery, bot: Bot):
    """Отображает настройки обучения"""
    await callback.message.edit_text(
        "⚙️ *Настройки обучения*\n\n"
        "Здесь вы можете настроить количество слов для теста и заучивания.",
        parse_mode="Markdown",
        reply_markup=learning_settings_keyboard()
    )
    await callback.answer()

# Заменить функцию handle_test_settings:

async def handle_test_settings(callback: types.CallbackQuery, bot: Bot):
    """Обработчик настроек теста по словарю"""
    chat_id = callback.from_user.id
    user = crud.get_user(chat_id)
    if not user:
        await callback.answer("Профиль не найден. Используйте /start.", show_alert=True)
        return
    
    # Получаем текущее количество слов для теста
    test_words_count = get_user_setting(user, USER_TEST_WORDS_COUNT, 5)
    memorize_words_count = get_user_setting(user, USER_MEMORIZE_WORDS_COUNT, 5)
    
    await callback.message.edit_text(
        f"📊 *Настройки теста по словарю*\n\n"
        f"Текущие настройки:\n"
        f"• Количество слов в тесте: *{test_words_count}*\n"
        f"• Количество слов в заучивании: *{memorize_words_count}*\n\n"
        f"Выберите количество слов для теста (от 1 до 20):\n"
        f"Если в словаре меньше слов, чем указано, будут использованы все доступные слова.",
        parse_mode="Markdown",
        reply_markup=test_words_count_keyboard()
    )
    await callback.answer()

# Заменить функцию handle_memorize_settings:

async def handle_memorize_settings(callback: types.CallbackQuery, bot: Bot):
    """Обработчик настроек заучивания сета"""
    chat_id = callback.from_user.id
    user = crud.get_user(chat_id)
    if not user:
        await callback.answer("Профиль не найден. Используйте /start.", show_alert=True)
        return
    
    # Получаем текущее количество слов для заучивания
    test_words_count = get_user_setting(user, USER_TEST_WORDS_COUNT, 5)
    memorize_words_count = get_user_setting(user, USER_MEMORIZE_WORDS_COUNT, 5)
    
    await callback.message.edit_text(
        f"📝 *Настройки заучивания сета*\n\n"
        f"Текущие настройки:\n"
        f"• Количество слов в тесте: *{test_words_count}*\n"
        f"• Количество слов в заучивании: *{memorize_words_count}*\n\n"
        f"Выберите количество слов для заучивания (от 1 до 20):",
        parse_mode="Markdown",
        reply_markup=memorize_words_count_keyboard()
    )
    await callback.answer()

async def handle_test_count_selection(callback: types.CallbackQuery, bot: Bot):
    """Обработчик выбора количества слов для теста."""
    chat_id = callback.from_user.id
    try:
        _, _, count_str = callback.data.split(":", 2)
        count = int(count_str)
        
        if not (1 <= count <= 20):
            await callback.answer("Ошибка: недопустимое количество слов", show_alert=True)
            return
        
        # Обновляем в базе данных
        try:
            # Обновляем количество слов для теста
            crud.update_user_test_words_count(chat_id, count)
            logger.info(f"Обновлено количество слов для теста у пользователя {chat_id}: {count}")
            
            # Получаем обновленные настройки
            user = crud.get_user(chat_id)
            test_words_count = get_user_setting(user, USER_TEST_WORDS_COUNT, count)
            memorize_words_count = get_user_setting(user, USER_MEMORIZE_WORDS_COUNT, 5)
            
            # Отправляем подтверждение
            await callback.message.edit_text(
                f"✅ Настройки обучения обновлены!\n\n"
                f"📊 Количество слов в тесте: *{test_words_count}*\n"
                f"📝 Количество слов в заучивании: *{memorize_words_count}*",
                parse_mode="Markdown",
                reply_markup=learning_settings_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении количества слов для теста: {e}")
            await callback.message.edit_text(
                "❌ Произошла ошибка при обновлении настроек.",
                reply_markup=learning_settings_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка в обработчике выбора количества слов для теста: {e}")
        await callback.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")
    
    await callback.answer()

async def handle_memorize_count_selection(callback: types.CallbackQuery, bot: Bot):
    """Обработчик выбора количества слов для заучивания."""
    chat_id = callback.from_user.id
    try:
        _, _, count_str = callback.data.split(":", 2)
        count = int(count_str)
        
        if not (1 <= count <= 20):
            await callback.answer("Ошибка: недопустимое количество слов", show_alert=True)
            return
        
        # Обновляем в базе данных
        try:
            # Обновляем количество слов для заучивания
            crud.update_user_memorize_words_count(chat_id, count)
            logger.info(f"Обновлено количество слов для заучивания у пользователя {chat_id}: {count}")
            
            # Получаем обновленные настройки
            user = crud.get_user(chat_id)
            test_words_count = get_user_setting(user, USER_TEST_WORDS_COUNT, 5)
            memorize_words_count = get_user_setting(user, USER_MEMORIZE_WORDS_COUNT, count)
            
            # Отправляем подтверждение
            await callback.message.edit_text(
                f"✅ Настройки обучения обновлены!\n\n"
                f"📊 Количество слов в тесте: *{test_words_count}*\n"
                f"📝 Количество слов в заучивании: *{memorize_words_count}*",
                parse_mode="Markdown",
                reply_markup=learning_settings_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении количества слов для заучивания: {e}")
            await callback.message.edit_text(
                "❌ Произошла ошибка при обновлении настроек.",
                reply_markup=learning_settings_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка в обработчике выбора количества слов для заучивания: {e}")
        await callback.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")
    
    await callback.answer()

# Отдельная функция для проверки числа
def is_valid_number(text):
    """Проверяет, является ли текст числом от 1 до 20"""
    if not text.isdigit():
        return False
    value = int(text)
    return 1 <= value <= 20

async def process_learning_settings_input(message: types.Message, bot: Bot):
    """Обработчик ввода количества слов для теста/заучивания"""
    chat_id = message.chat.id
    text = message.text.strip()
    
    # Проверяем, что это числовое сообщение
    if not text.isdigit():
        if chat_id not in pending_learning_settings:
            return False
        else:
            await message.answer(
                "⚠️ Ошибка: введите корректное число.",
                reply_markup=learning_settings_keyboard()
            )
            return True
    
    value = int(text)
    if not (1 <= value <= 20):
        await message.answer(
            "⚠️ Ошибка: число должно быть от 1 до 20.",
            reply_markup=learning_settings_keyboard()
        )
        return True
    
    # Определяем тип настройки
    setting_type = None
    if chat_id in pending_learning_settings:
        setting_type = pending_learning_settings[chat_id]
        logger.info(f"Получен ввод настройки {setting_type} от пользователя {chat_id}: {value}")
    else:
        # Если не в контексте, ничего не делаем, т.к. не можем определить тип настройки
        return False
    
    try:
        if setting_type == "test_words":
            # Дополнительная логика для обновления настроек теста
            with db_manager.transaction() as conn:
                conn.execute("UPDATE users SET test_words_count = ? WHERE chat_id = ?", (value, chat_id))
            
            logger.info(f"Обновлено количество слов для теста у пользователя {chat_id}: {value}")
            
            if chat_id in pending_learning_settings:
                del pending_learning_settings[chat_id]
            
            await message.answer(
                f"✅ Количество слов для теста успешно установлено на {value}.",
                reply_markup=learning_settings_keyboard()
            )
            return True
            
        elif setting_type == "memorize_words":
            # Аналогично для заучивания
            with db_manager.transaction() as conn:
                conn.execute("UPDATE users SET memorize_words_count = ? WHERE chat_id = ?", (value, chat_id))
            
            logger.info(f"Обновлено количество слов для заучивания у пользователя {chat_id}: {value}")
            
            if chat_id in pending_learning_settings:
                del pending_learning_settings[chat_id]
            
            await message.answer(
                f"✅ Количество слов для заучивания успешно установлено на {value}.",
                reply_markup=learning_settings_keyboard()
            )
            return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении настроек для пользователя {chat_id}: {e}")
        if chat_id in pending_learning_settings:
            del pending_learning_settings[chat_id]
        
        await message.answer(
            "❌ Произошла ошибка при обновлении настроек. Пожалуйста, попробуйте позже.",
            reply_markup=learning_settings_keyboard()
        )
        return True
    
    return False

# Заменить функцию send_learning_test_question на следующую:
# Добавить в начало файла handlers/learning.py:

def format_progress_bar(current: int, total: int, length: int = 10) -> str:
    """Создает текстовую шкалу прогресса."""
    filled_length = int(length * current / total) if total > 0 else 0
    filled = "█" * filled_length
    empty = "░" * (length - filled_length)
    bar = filled + empty
    return f"[{bar}] {current}/{total}"


async def send_learning_test_question(chat_id, bot: Bot):
    """Отправляет вопрос теста/заучивания с корректным форматированием"""
    state = learning_test_states.get(chat_id)
    if not state:
        return
    
    if state["current_index"] >= len(state["questions"]):
        await finish_learning_test(chat_id, bot)
        return
    
    question = state["questions"][state["current_index"]]
    test_type = state.get("test_type", "")
    
    # Создаем специализированное форматирование для разных типов тестов
    current_index = state["current_index"] + 1
    total_questions = len(state["questions"])
    progress_bar = format_progress_bar(current_index, total_questions)
    
    # Определяем заголовок на основе типа теста
    if test_type == "dictionary":
        title = "📚 ТЕСТ ПО СЛОВАРЮ"
    else:  # memorize
        title = "📝 ЗАУЧИВАНИЕ СЕТА"
    
    # Форматируем сообщение с вопросом
    formatted_question = (
        f"{title}\n"
        f"{progress_bar}\n\n"
        f"Вопрос {current_index}/{total_questions}:\n\n"
        f"Какой перевод слова '*{question['word']}*'?"
    )
    
    # Создаем клавиатуру с вариантами ответов
    keyboard = learning_quiz_keyboard(question["options"], state["current_index"])
    
    await bot.send_message(
        chat_id, 
        formatted_question,
        parse_mode="Markdown", 
        reply_markup=keyboard
    )

# Заменить функцию process_learning_test_answer:

async def process_learning_test_answer(callback: types.CallbackQuery, bot: Bot):
    """Обрабатывает ответ на вопрос теста/заучивания"""
    from datetime import datetime
    
    chat_id = callback.from_user.id
    
    # Обработка навигационных действий
    if callback.data == "learn:back":
        from keyboards.main_menu import main_menu_keyboard
        await bot.send_message(chat_id, "Главное меню", reply_markup=main_menu_keyboard())
        if chat_id in learning_test_states:
            del learning_test_states[chat_id]
        await callback.answer()
        return
        
    if callback.data == "learn:stop":
        await bot.send_message(chat_id, "Тест остановлен.", reply_markup=learning_menu_keyboard())
        if chat_id in learning_test_states:
            del learning_test_states[chat_id]
        await callback.answer()
        return

    # Обработка ответа
    try:
        data = callback.data.split(":")
        if len(data) != 4:
            await callback.answer("Неверный формат данных.", show_alert=True)
            return
            
        _, _, q_index_str, option_index_str = data
        q_index = int(q_index_str)
        option_index = int(option_index_str)
        
        state = learning_test_states.get(chat_id)
        if not state:
            await callback.answer("Тест не найден.", show_alert=True)
            return
            
        if q_index != state["current_index"]:
            await callback.answer("Неверная последовательность вопросов.", show_alert=True)
            return
            
        question = state["questions"][q_index]
        test_type = state.get("test_type", "")
        
        # Проверяем ответ
        is_correct = (option_index == question["correct_index"])
        
        if is_correct:
            # Правильный ответ
            try:
                # Обработка в зависимости от типа теста
                if test_type == "dictionary":
                    # Это тест по словарю, слово уже в словаре
                    await callback.answer("Правильно!")
                elif test_type == "memorize":
                    # Это заучивание сета, слово НЕ добавляется в словарь
                    await callback.answer("Правильно! (Слово не добавляется в словарь)")
                else:
                    # Неизвестный тип теста, на всякий случай
                    await callback.answer("Правильно!")
                    
                state["correct"] += 1
            except Exception as e:
                logger.error(f"Ошибка при обработке правильного ответа: {e}")
                await callback.answer("Правильно, но возникла ошибка при обработке результата.")
        else:
            # Неправильный ответ
            await callback.answer(f"Неправильно! Правильный ответ: {question['correct']}")
            
        # Переходим к следующему вопросу
        state["current_index"] += 1
        await send_learning_test_question(chat_id, bot)
    except ValueError as e:
        logger.error(f"Ошибка формата при обработке ответа на тест: {e}")
        await callback.answer("Ошибка при обработке ответа. Некорректный формат данных.")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при обработке ответа на тест: {e}")
        await callback.answer("Произошла ошибка при обработке ответа. Пожалуйста, попробуйте снова.")

# Заменить функцию finish_learning_test:

async def finish_learning_test(chat_id, bot: Bot):
    """Завершает тест и показывает результаты"""
    state = learning_test_states.get(chat_id)
    if not state:
        return
    
    # Формируем сообщение с результатами
    correct = state['correct']
    total = len(state['questions'])
    percentage = (correct / total) * 100 if total > 0 else 0
    
    # Выбираем эмодзи на основе результата
    if percentage >= 90:
        emoji = "🎉"
    elif percentage >= 70:
        emoji = "👍"
    elif percentage >= 50:
        emoji = "👌"
    else:
        emoji = "🔄"
    
    # Создаем шкалу прогресса
    progress = format_progress_bar(correct, total, 20)
    
    # Формируем заголовок в зависимости от типа теста
    if state['test_type'] == "dictionary":
        header = f"{emoji} Тест по словарю завершен! {emoji}"
    else:  # memorize
        header = f"{emoji} Заучивание сета завершено! {emoji}"
    
    message = f"{header}\n\n"
    message += f"*Счет:* {correct} из {total} ({percentage:.1f}%)\n{progress}\n\n"
    
    # Дополнительная информация в зависимости от типа теста
    if state['test_type'] == "dictionary":
        message += "Тест проверял ваше знание слов из вашего словаря.\n\n"
    else:  # memorize
        message += "Заучивание не добавляет слова в ваш словарь. Используйте Квиз для этого.\n\n"
    
    # Советы в зависимости от результата
    if percentage < 70:
        message += "💡 *Совет:* Регулярное повторение поможет лучше запомнить слова."
    
    # Создаем клавиатуру
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Главное меню", callback_data="menu:back"))
    keyboard.add(types.InlineKeyboardButton("Вернуться к обучению", callback_data="learning:back"))
    
    await bot.send_message(
        chat_id, 
        message,
        parse_mode="Markdown", 
        reply_markup=keyboard
    )
    
    # Отправляем стикер при хорошем результате
    if percentage >= 70:
        from utils.sticker_helper import get_congratulation_sticker
        sticker_id = get_congratulation_sticker()
        if sticker_id:
            await bot.send_sticker(chat_id, sticker_id)
    
    # Удаляем состояние теста
    del learning_test_states[chat_id]

# Заменить функцию register_learning_handlers:

def register_learning_handlers(dp: Dispatcher, bot: Bot):
    """Регистрирует обработчики для меню обучения"""
    # ВАЖНО: Обработчик для ввода настроек регистрируем первым
    dp.register_message_handler(
        partial(process_learning_settings_input, bot=bot),
        lambda message: message.text and message.text.strip().isdigit() or message.chat.id in pending_learning_settings,
        content_types=['text'],
        state="*"  # Обрабатываем в любом состоянии
    )
    # Регистрируем обработчики для кнопок выбора количества слов
    dp.register_callback_query_handler(
        partial(handle_test_count_selection, bot=bot),
        lambda c: c.data and c.data.startswith("learn:test_count:")
    )
    
    dp.register_callback_query_handler(
        partial(handle_memorize_count_selection, bot=bot),
        lambda c: c.data and c.data.startswith("learn:memorize_count:")
    )
    # Остальные обработчики регистрируем после
    dp.register_callback_query_handler(
        partial(handle_learning_menu, bot=bot),
        lambda c: c.data == "menu:learning"
    )
    
    dp.register_callback_query_handler(
        partial(handle_learning_menu, bot=bot),
        lambda c: c.data == "learning:back"
    )
    
    dp.register_callback_query_handler(
        partial(handle_learning_settings, bot=bot),
        lambda c: c.data == "learning:settings"
    )
    
    dp.register_callback_query_handler(
        partial(handle_test_settings, bot=bot),
        lambda c: c.data == "learning:test_settings"
    )
    
    dp.register_callback_query_handler(
        partial(handle_memorize_settings, bot=bot),
        lambda c: c.data == "learning:memorize_settings"
    )
    
    dp.register_callback_query_handler(
        partial(handle_dictionary_test, bot=bot),
        lambda c: c.data == "learning:dictionary_test"
    )
    
    dp.register_callback_query_handler(
        partial(handle_memorize_set, bot=bot),
        lambda c: c.data == "learning:memorize_set"
    )
    
    dp.register_callback_query_handler(
        partial(process_learning_test_answer, bot=bot),
        lambda c: c.data and c.data.startswith("learn:answer:")
    )
    
    dp.register_callback_query_handler(
        partial(process_learning_test_answer, bot=bot),
        lambda c: c.data in ["learn:back", "learn:stop"]
    )

def learning_quiz_keyboard(options, question_index):
    """Создает клавиатуру для теста обучения с отдельными callback_data."""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for i, option in enumerate(options):
        keyboard.add(types.InlineKeyboardButton(option, callback_data=f"learn:answer:{question_index}:{i}"))
    keyboard.add(
        types.InlineKeyboardButton("Назад", callback_data="learn:back"),
        types.InlineKeyboardButton("Остановить тест", callback_data="learn:stop")
    )
    return keyboard