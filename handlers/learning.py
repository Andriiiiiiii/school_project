
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

async def handle_test_settings(callback: types.CallbackQuery, bot: Bot):
    """Обработчик настроек теста по словарю"""
    chat_id = callback.from_user.id
    user = crud.get_user(chat_id)
    if not user:
        await callback.answer("Профиль не найден. Используйте /start.", show_alert=True)
        return
    
    # Получаем текущее количество слов для теста (по умолчанию 5)
    test_words_count = user[7] if len(user) > 7 and user[7] else 5
    
    # Регистрируем ожидание ввода
    pending_learning_settings[chat_id] = "test_words"
    logger.info(f"Пользователь {chat_id} переходит в режим ввода test_words")
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="learning:settings"))
    
    await callback.message.edit_text(
        f"📊 *Настройки теста по словарю*\n\n"
        f"Текущее количество слов в тесте: *{test_words_count}*\n\n"
        f"Введите новое количество слов (от 1 до 20):\n"
        f"Если в словаре меньше слов, чем указано, будут использованы все доступные слова.",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()



async def handle_memorize_settings(callback: types.CallbackQuery, bot: Bot):
    """Обработчик настроек заучивания сета"""
    chat_id = callback.from_user.id
    user = crud.get_user(chat_id)
    if not user:
        await callback.answer("Профиль не найден. Используйте /start.", show_alert=True)
        return
    
    # Получаем текущее количество слов для заучивания (по умолчанию 5)
    memorize_words_count = user[8] if len(user) > 8 and user[8] else 5
    
    # Регистрируем ожидание ввода
    pending_learning_settings[chat_id] = "memorize_words"
    logger.info(f"Пользователь {chat_id} переходит в режим ввода memorize_words")
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="learning:settings"))
    
    await callback.message.edit_text(
        f"📝 *Настройки заучивания сета*\n\n"
        f"Текущее количество слов в заучивании: *{memorize_words_count}*\n\n"
        f"Введите новое количество слов (от 1 до 20):",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()

# Отдельная функция для проверки числа
def is_valid_number(text):
    """Проверяет, является ли текст числом от 1 до 20"""
    if not text.isdigit():
        return False
    value = int(text)
    return 1 <= value <= 20

async def handle_memorize_set(callback: types.CallbackQuery, bot: Bot):
    """Обработчик запуска заучивания сета"""
    chat_id = callback.from_user.id
    
    # Получаем информацию о пользователе
    from database import crud
    user = crud.get_user(chat_id)
    if not user:
        await callback.answer("Профиль не найден. Используйте /start.", show_alert=True)
        return
    
    # Получаем уровень и выбранный сет
    level = user[1]
    
    # Проверяем, выбран ли сет в профиле
    chosen_set = None
    if len(user) > 6 and user[6]:
        chosen_set = user[6]
    
    # Проверяем в кэше для большей надежности
    from handlers.settings import user_set_selection
    if not chosen_set and chat_id in user_set_selection:
        chosen_set = user_set_selection[chat_id]
    
    # Если сет все еще не определен, используем значение по умолчанию
    if not chosen_set:
        from config import DEFAULT_SETS
        chosen_set = DEFAULT_SETS.get(level)
        if chosen_set:
            crud.update_user_chosen_set(chat_id, chosen_set)
            user_set_selection[chat_id] = chosen_set
    
    # Проверяем наличие файла сета
    import os
    from config import LEVELS_DIR
    set_file_path = os.path.join(LEVELS_DIR, level, f"{chosen_set}.txt")
    if not os.path.exists(set_file_path):
        await callback.message.edit_text(
            f"⚠️ Ошибка: не найден файл для сета '{chosen_set}' уровня {level}.\n"
            f"Пожалуйста, выберите другой сет в настройках.",
            parse_mode="Markdown",
            reply_markup=learning_menu_keyboard()
        )
        await callback.answer()
        return
    
    # Загружаем слова из сета
    set_words = []
    try:
        with open(set_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    set_words.append(line)
    except UnicodeDecodeError:
        try:
            with open(set_file_path, 'r', encoding='cp1251') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        set_words.append(line)
        except Exception as e:
            logger.error(f"Ошибка при чтении файла сета: {e}")
            await callback.message.edit_text(
                f"⚠️ Ошибка при чтении файла сета.",
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
    
    # Получаем количество слов для заучивания
    memorize_words_count = user[8] if len(user) > 8 and user[8] else 5
    memorize_words_count = min(memorize_words_count, len(set_words))
    
    # Выбираем случайные слова из сета
    selected_words = random.sample(set_words, memorize_words_count)
    
    # Получаем уже выученные слова
    learned_raw = crud.get_learned_words(chat_id)
    learned_set = set(extract_english(item[0]).lower() for item in learned_raw)
    
    # Загружаем данные для квиза
    from utils.quiz_helpers import load_quiz_data
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
        english_word = extract_english(word_line).lower()
        
        # Определяем правильный перевод
        if " - " in word_line:
            correct_translation = word_line.split(" - ", 1)[1].strip()
        elif " – " in word_line:
            correct_translation = word_line.split(" – ", 1)[1].strip()
        elif ": " in word_line:
            correct_translation = word_line.split(": ", 1)[1].strip()
        else:
            # Если нет разделителя, используем перевод из словаря
            correct_translation = translations.get(english_word, english_word)
        
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
        
        # Определяем, является ли это повторением или изучением нового слова
        is_revision = english_word.lower() in learned_set
        
        questions.append({
            "word": english_word,  # Только английское слово вместо всей строки
            "correct": correct_translation,
            "options": options,
            "correct_index": correct_index,
            "is_revision": is_revision
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

# Обработчик текстовых сообщений для настроек
async def process_learning_settings_input(message: types.Message, bot: Bot):
    """Обработчик ввода количества слов для теста/заучивания"""
    chat_id = message.chat.id
    
    # Проверяем, ожидаем ли ввод настроек от этого пользователя
    if chat_id not in pending_learning_settings:
        logger.debug(f"Chat ID {chat_id} не найден в pending_learning_settings, пропускаем обработку")
        return False  # Возвращаем False, чтобы другие обработчики могли обработать сообщение
    
    setting_type = pending_learning_settings[chat_id]  # Не удаляем пока из словаря
    text = message.text.strip()
    
    logger.info(f"Получен ввод настройки {setting_type} от пользователя {chat_id}: {text}")
    
    if not text.isdigit():
        await message.answer(
            "⚠️ Ошибка: введите корректное число.",
            reply_markup=learning_settings_keyboard()
        )
        return True  # Возвращаем True, чтобы предотвратить обработку другими обработчиками
    
    value = int(text)
    if not (1 <= value <= 20):
        await message.answer(
            "⚠️ Ошибка: число должно быть от 1 до 20.",
            reply_markup=learning_settings_keyboard()
        )
        return True
    
    try:
        if setting_type == "test_words":
            # Используем crud функцию для обновления настройки теста
            crud.update_user_test_words_count(chat_id, value)
            logger.info(f"Обновлено количество слов для теста у пользователя {chat_id}: {value}")
            
            # Удаляем пользователя из режима ожидания ввода
            del pending_learning_settings[chat_id]
            
            await message.answer(
                f"✅ Количество слов для теста успешно установлено на {value}.",
                reply_markup=learning_settings_keyboard()
            )
        elif setting_type == "memorize_words":
            # Используем crud функцию для обновления настройки заучивания
            crud.update_user_memorize_words_count(chat_id, value)
            logger.info(f"Обновлено количество слов для заучивания у пользователя {chat_id}: {value}")
            
            # Удаляем пользователя из режима ожидания ввода
            del pending_learning_settings[chat_id]
            
            await message.answer(
                f"✅ Количество слов для заучивания успешно установлено на {value}.",
                reply_markup=learning_settings_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка при обновлении настроек для пользователя {chat_id}: {e}")
        # Удаляем пользователя из режима ожидания ввода даже при ошибке
        if chat_id in pending_learning_settings:
            del pending_learning_settings[chat_id]
            
        await message.answer(
            "❌ Произошла ошибка при обновлении настроек. Пожалуйста, попробуйте позже.",
            reply_markup=learning_settings_keyboard()
        )
    
    return True  # Предотвращаем обработку другими обработчиками


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
    test_words_count = user[7] if len(user) > 7 and user[7] else 5
    logger.info(f"Пользователь {chat_id} запускает тест по словарю с {test_words_count} словами")
    
    # Проверяем, хватает ли слов в словаре
    if test_words_count > len(learned_words):
        logger.info(f"В словаре пользователя {chat_id} меньше слов ({len(learned_words)}), чем запрошено ({test_words_count})")
        test_words_count = len(learned_words)
    
    # Выбираем случайные слова из словаря
    selected_words = random.sample(learned_words, test_words_count)
    
    # Получаем данные для квиза из текущего уровня
    level = user[1]
    chosen_set = user[6] if len(user) > 6 and user[6] else None
    
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
    
    # Если сет не найден в базе данных, устанавливаем стандартный
    if not chosen_set:
        from config import DEFAULT_SETS
        chosen_set = DEFAULT_SETS.get(level)
        if chosen_set:
            # Обновляем базу данных и кэш
            crud.update_user_chosen_set(chat_id, chosen_set)
            from handlers.settings import user_set_selection
            user_set_selection[chat_id] = chosen_set
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
        # Тут логика проверки и поиска файла (сокращено для простоты)
        await callback.message.edit_text(
            f"⚠️ Ошибка: не найден файл для сета '{chosen_set}' уровня {level}.\n"
            f"Пожалуйста, выберите другой сет в настройках.",
            parse_mode="Markdown",
            reply_markup=learning_menu_keyboard()
        )
        await callback.answer()
        return
    
    # Загружаем слова из сета
    set_words = []
    try:
        with open(set_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    set_words.append(line)
    except UnicodeDecodeError:
        try:
            with open(set_file_path, 'r', encoding='cp1251') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        set_words.append(line)
        except Exception as e:
            logger.error(f"Ошибка при чтении файла сета: {e}")
            await callback.message.edit_text(
                f"⚠️ Ошибка при чтении файла сета.",
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
    memorize_words_count = user[8] if len(user) > 8 and user[8] else 5
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
        
        if " - " in word_line:
            parts = word_line.split(" - ", 1)
            english_part = parts[0].strip()
            russian_part = parts[1].strip() if len(parts) > 1 else ""
        elif " – " in word_line:
            parts = word_line.split(" – ", 1)
            english_part = parts[0].strip()
            russian_part = parts[1].strip() if len(parts) > 1 else ""
        elif ": " in word_line:
            parts = word_line.split(": ", 1)
            english_part = parts[0].strip()
            russian_part = parts[1].strip() if len(parts) > 1 else ""
        else:
            english_part = extract_english(word_line)
            russian_part = translations.get(english_part.lower(), "")
        
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
        "is_revision": False,
        "test_type": "memorize"
    }
    
    # Начинаем тест
    await callback.answer()
    await send_learning_test_question(chat_id, bot)

async def send_learning_test_question(chat_id, bot: Bot):
    """Отправляет вопрос теста/заучивания"""
    from utils.visual_helpers import format_quiz_question
    
    state = learning_test_states.get(chat_id)
    if not state:
        return
    
    if state["current_index"] >= len(state["questions"]):
        await finish_learning_test(chat_id, bot)
        return
    
    question = state["questions"][state["current_index"]]
    test_type = state.get("test_type", "")
    
    # Добавляем отладочную запись
    logger.debug(f"Вопрос слово: '{question['word']}', перевод: '{question['correct']}'")
    
    # Определяем заголовок в зависимости от типа теста
    if test_type == "dictionary":
        title = "📚 ТЕСТ ПО СЛОВАРЮ"
    else:  # memorize
        title = "📝 ЗАУЧИВАНИЕ СЕТА"
    
    formatted_question = format_quiz_question(
        state["current_index"] + 1,
        len(state["questions"]),
        question["word"],  # Здесь должно быть только английское слово
        question["options"],
        question.get("is_revision", False)  # Учитываем режим повторения
    )
    
    # Заменяем заголовок на правильный
    formatted_question = formatted_question.replace("🎯 СЛОВАРНЫЙ КВИЗ", title)
    formatted_question = formatted_question.replace("🔄 ПОВТОРЕНИЕ", title)
    
    # Создаем клавиатуру с вариантами ответов
    keyboard = learning_quiz_keyboard(question["options"], state["current_index"])
    
    await bot.send_message(
        chat_id, 
        formatted_question,
        parse_mode="Markdown", 
        reply_markup=keyboard
    )

async def process_learning_test_answer(callback: types.CallbackQuery, bot: Bot):
    """Обрабатывает ответ на вопрос теста/заучивания"""
    from datetime import datetime
    
    if callback.data == "learn:back":
        from keyboards.main_menu import main_menu_keyboard
        await bot.send_message(callback.from_user.id, "Главное меню", reply_markup=main_menu_keyboard())
        if callback.from_user.id in learning_test_states:
            del learning_test_states[callback.from_user.id]
        await callback.answer()
        return
        
    if callback.data == "learn:stop":
        await bot.send_message(callback.from_user.id, "Тест остановлен.", reply_markup=learning_menu_keyboard())
        if callback.from_user.id in learning_test_states:
            del learning_test_states[callback.from_user.id]
        await callback.answer()
        return

    # Обработка ответа
    data = callback.data.split(":")
    if len(data) != 4:
        await callback.answer("Неверный формат данных.", show_alert=True)
        return
        
    _, _, q_index_str, option_index_str = data
    q_index = int(q_index_str)
    option_index = int(option_index_str)
    
    chat_id = callback.from_user.id
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
    if option_index == question["correct_index"]:
        # Правильный ответ
        try:
            # В случае теста по словарю или заучивания сета НЕ добавляем слова в словарь
            # Слова добавляются в словарь только через квиз
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

async def finish_learning_test(chat_id, bot: Bot):
    """Завершает тест и показывает результаты"""
    from utils.visual_helpers import format_result_message
    
    state = learning_test_states.get(chat_id)
    if not state:
        return
    
    # Формируем сообщение с результатами
    result_message = format_result_message(
        state['correct'], 
        len(state['questions']),
        state['test_type'] == "dictionary"  # dictionary = всегда режим повторения
    )
    
    # Создаем клавиатуру
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Главное меню", callback_data="menu:back"))
    keyboard.add(types.InlineKeyboardButton("Вернуться к обучению", callback_data="learning:back"))
    
    await bot.send_message(
        chat_id, 
        result_message,
        parse_mode="Markdown", 
        reply_markup=keyboard
    )
    
    # Отправляем стикер при хорошем результате
    if state['correct'] / len(state['questions']) >= 0.7:
        from utils.sticker_helper import get_congratulation_sticker
        sticker_id = get_congratulation_sticker()
        if sticker_id:
            await bot.send_sticker(chat_id, sticker_id)
    
    del learning_test_states[chat_id]

def register_learning_handlers(dp: Dispatcher, bot: Bot):
    """Регистрирует обработчики для меню обучения"""
    # ВАЖНО: Обработчик для ввода настроек регистрируем первым
    dp.register_message_handler(
        partial(process_learning_settings_input, bot=bot),
        lambda message: message.chat.id in pending_learning_settings and message.text,
        content_types=['text'],
        state="*"  # Обрабатываем в любом состоянии
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

async def process_direct_settings_update(message: types.Message, bot: Bot):
    """Прямая обработка ввода числовых настроек"""
    chat_id = message.chat.id
    text = message.text.strip()
    
    # Проверяем, что это числовое сообщение
    if not text.isdigit():
        return
    
    value = int(text)
    if not (1 <= value <= 20):
        await message.answer("⚠️ Ошибка: число должно быть от 1 до 20.")
        return
    
    # Проверяем контекст - какие настройки сейчас редактируются
    # Получаем последнее сообщение бота
    try:
        messages = []
        async for msg in bot.get_chat_history(chat_id, limit=3):
            if msg.from_user.is_bot and msg.text:
                if "Настройки теста по словарю" in msg.text:
                    # Обновляем количество слов для теста
                    from database.db import db_manager
                    with db_manager.get_cursor() as cursor:
                        cursor.execute("UPDATE users SET test_words_count = ? WHERE chat_id = ?", (value, chat_id))
                        db_manager.conn.commit()
                    
                    await message.answer(
                        f"✅ Количество слов для теста установлено на {value}.",
                        reply_markup=learning_settings_keyboard()
                    )
                    return
                    
                elif "Настройки заучивания сета" in msg.text:
                    # Обновляем количество слов для заучивания
                    from database.db import db_manager
                    with db_manager.get_cursor() as cursor:
                        cursor.execute("UPDATE users SET memorize_words_count = ? WHERE chat_id = ?", (value, chat_id))
                        db_manager.conn.commit()
                    
                    await message.answer(
                        f"✅ Количество слов для заучивания установлено на {value}.",
                        reply_markup=learning_settings_keyboard()
                    )
                    return
    except Exception as e:
        logger.error(f"Ошибка при обработке настроек: {e}")