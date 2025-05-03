# handlers/quiz.py
import random
from datetime import datetime
from aiogram import types, Dispatcher, Bot
import asyncio
from database import crud  # Убедимся, что импорт crud глобальный
from utils.quiz_helpers import load_quiz_data
from keyboards.submenus import quiz_keyboard
from utils.helpers import get_daily_words_for_user, daily_words_cache
from utils.visual_helpers import format_quiz_question, format_result_message, extract_english
from config import REMINDER_START, DURATION_HOURS
import logging
# Импортируем визуальные помощники и работу со стикерами
from utils.sticker_helper import get_congratulation_sticker
# Настройка логирования
logger = logging.getLogger(__name__)

# Глобальный словарь для хранения состояния квиза для каждого пользователя
quiz_states = {}

def generate_quiz_questions_from_daily(daily_words, level, chosen_set=None, is_revision_mode=False):
    """
    Генерирует вопросы для квиза на основе слов дня.
    Улучшенная версия, которая избегает дубликатов вариантов ответов, где это возможно.
    
    Параметры:
    - daily_words: список слов дня
    - level: уровень пользователя
    - chosen_set: выбранный набор слов (если указан)
    - is_revision_mode: режим повторения (True/False)
    """
    quiz_data = load_quiz_data(level, chosen_set)
    if not quiz_data:
        logger.warning(f"No quiz data found for level {level}, set {chosen_set}")
        return []
    
    mapping = {item["word"].lower(): item["translation"] for item in quiz_data}
    translations_set = set(item["translation"] for item in quiz_data)
    questions = []
    
    for word in daily_words:
        word_lc = word.lower()
        
        # Пытаемся найти слово в словаре соответствий
        if word_lc in mapping:
            correct_translation = mapping[word_lc]
        else:
            # Если не нашли слово, пробуем извлечь английскую часть
            word_extracted = extract_english(word).lower()
            if word_extracted in mapping:
                correct_translation = mapping[word_extracted]
            else:
                # Если все равно не нашли, логируем и пропускаем
                logger.warning(f"Word '{word}' (extracted as '{word_extracted}') not found in quiz data mapping")
                continue
        
        # Создаем пул отвлекающих вариантов, исключая правильный ответ
        pool = list(translations_set - {correct_translation})
        
        # Выбираем отвлекающие варианты в зависимости от размера пула
        if len(pool) >= 3:
            # Если достаточно вариантов, используем random.sample для уникальных вариантов
            distractors = random.sample(pool, 3)
        else:
            # Если недостаточно вариантов, используем random.choices, что может дать дубликаты,
            # но это лучше, чем искусственные варианты
            if pool:
                distractors = random.choices(pool, k=3)
            else:
                # В крайнем случае, если совсем нет отвлекающих вариантов
                logger.warning(f"No distractors available for word '{word}'")
                distractors = ["???", "???", "???"]
        
        options = [correct_translation] + distractors
        random.shuffle(options)
        correct_index = options.index(correct_translation)
        
        questions.append({
            "word": word,
            "correct": correct_translation,
            "options": options,
            "correct_index": correct_index,
            "is_revision": is_revision_mode  # Добавляем информацию о режиме повторения
        })
    
    return questions

async def start_quiz(callback: types.CallbackQuery, bot: Bot):
    """
    Initializes a quiz for the user.
    Enhanced with better error handling and using shared quiz utilities.
    """
    chat_id = callback.from_user.id
    try:
        user = crud.get_user(chat_id)
        if not user:
            await bot.send_message(chat_id, "Профиль не найден. Используйте /start.")
            return
        level = user[1]
        
        # Get chosen set from settings
        try:
            from handlers.settings import user_set_selection
            chosen_set = user_set_selection.get(chat_id)
        except ImportError:
            logger.error("Error importing user_set_selection, using default set")
            chosen_set = None
        
        # Get learned words efficiently
        try:
            learned_raw = crud.get_learned_words(chat_id)
            learned_set = set(extract_english(item[0]).lower() for item in learned_raw)
            logger.info(f"User {chat_id} has {len(learned_set)} learned words")
        except Exception as e:
            logger.error(f"Error getting learned words for user {chat_id}: {e}")
            learned_set = set()
        
        # Get daily words with proper error handling
        try:
            result = get_daily_words_for_user(
                chat_id, level, user[2], user[3],
                first_time=REMINDER_START, 
                duration_hours=DURATION_HOURS,
                chosen_set=chosen_set
            )
            
            if result is None:
                await bot.send_message(chat_id, "⚠️ Нет слов для квиза.")
                return
                
            # Get the cache entry
            if chat_id not in daily_words_cache:
                logger.error(f"Cache not found for user {chat_id}")
                await bot.send_message(chat_id, "Ошибка при получении слов дня. Пожалуйста, попробуйте позже.")
                return
                
            # Process the words
            daily_entry = daily_words_cache[chat_id]
            raw_words = [msg.replace("🔹 ", "").strip() for msg in daily_entry[1]]
            
            # Remove prefix message if present
            if raw_words and (raw_words[0].startswith("🎓") or raw_words[0].startswith("⚠️")):
                raw_words = raw_words[1:]
                
            # Extract English words and normalize to lowercase
            daily_words = [extract_english(line).lower() for line in raw_words]
            daily_words_set = set(daily_words)
            
            # Check revision mode
            is_revision_mode = len(daily_entry) > 9 and daily_entry[9]
            logger.info(f"User {chat_id} in revision mode: {is_revision_mode}")
            
            # Filter unlearned words
            unlearned_words = daily_words_set - learned_set
            
            # Determine which words to use in the quiz
            quiz_words = []
            if is_revision_mode:
                quiz_words = list(daily_words)
                await bot.send_message(
                    chat_id, 
                    "📝 *Режим повторения*: слова уже добавлены в Ваш словарь.",
                    parse_mode="Markdown"
                )
            else:
                quiz_words = list(unlearned_words)
                if not quiz_words:
                    await bot.send_message(
                        chat_id, 
                        "Все слова из раздела 'Слова дня' уже выучены! Попробуйте завтра или выберите новый набор слов."
                    )
                    return
                await bot.send_message(
                    chat_id, 
                    "📝 *Квиз по новым словам*: правильные ответы будут добавлены в Ваш словарь.",
                    parse_mode="Markdown"
                )
            
            # Generate questions using the shared utility
            from utils.quiz_helpers import load_quiz_data
            quiz_data = load_quiz_data(level, chosen_set)
            
            if not quiz_data:
                await bot.send_message(
                    chat_id, 
                    f"⚠️ Ошибка: не удалось загрузить данные квиза для уровня {level}."
                )
                return
                
            # Create translation mapping
            translations = {item["word"].lower(): item["translation"] for item in quiz_data}
            all_translations = list(translations.values())
            
            # Create questions
            from utils.quiz_utils import generate_quiz_options
            
            questions = []
            for word in quiz_words:
                # Find the correct translation
                if word in translations:
                    correct_translation = translations[word]
                else:
                    # Try to find it in the quiz data
                    found = False
                    for item in quiz_data:
                        if extract_english(item["word"]).lower() == word:
                            correct_translation = item["translation"]
                            found = True
                            break
                            
                    if not found:
                        logger.warning(f"Translation not found for word '{word}'")
                        continue
                
                # Generate options with the utility function
                options, correct_index = generate_quiz_options(
                    correct_translation, 
                    all_translations, 
                    4  # 4 options including the correct one
                )
                
                questions.append({
                    "word": word,
                    "correct": correct_translation,
                    "options": options,
                    "correct_index": correct_index,
                    "is_revision": is_revision_mode
                })
            
            if not questions:
                await bot.send_message(
                    chat_id, 
                    "⚠️ Не удалось создать вопросы для квиза."
                )
                return
                
            # Save quiz state
            quiz_states[chat_id] = {
                "questions": questions,
                "current_index": 0,
                "correct": 0,
                "is_revision": is_revision_mode
            }
            
            # Start the quiz
            await send_quiz_question(chat_id, bot)
            
        except Exception as e:
            logger.error(f"Error setting up quiz for user {chat_id}: {e}")
            await bot.send_message(
                chat_id, 
                "Произошла ошибка при настройке квиза. Пожалуйста, попробуйте позже."
            )
    except Exception as e:
        logger.error(f"Unhandled error in start_quiz for user {chat_id}: {e}")
        await bot.send_message(
            chat_id, 
            "Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже."
        )
    
    await callback.answer()

async def send_quiz_question(chat_id, bot: Bot):
    """Отправляет вопрос квиза."""
    try:
        state = quiz_states.get(chat_id)
        if not state:
            return
        
        current_index = state["current_index"]
        questions = state["questions"]
        
        if current_index >= len(questions):
            # Квиз завершен, отправляем результат
            from utils.visual_helpers import format_result_message
            result_message = format_result_message(state['correct'], len(questions), state.get('is_revision', False))
            await bot.send_message(chat_id, result_message, parse_mode="Markdown")
            
            # Отправляем стикер при хорошем результате и показываем главное меню
            score_percentage = (state['correct'] / len(questions)) * 100 if len(questions) > 0 else 0
            if score_percentage >= 70:
                from utils.sticker_helper import send_sticker_with_menu, get_congratulation_sticker
                await send_sticker_with_menu(chat_id, bot, get_congratulation_sticker())
                
                # Add only main menu button
                from keyboards.reply_keyboards import get_main_menu_keyboard
                await bot.send_message(
                    chat_id,
                    "Квиз завершен.",
                    reply_markup=get_main_menu_keyboard()
                )
            else:
                # Even if no sticker, still show main menu
                from keyboards.main_menu import main_menu_keyboard
                await bot.send_message(
                    chat_id,
                    "Выберите действие:",
                    reply_markup=main_menu_keyboard()
                )
                
                # Add only main menu button
                from keyboards.reply_keyboards import get_main_menu_keyboard
                await bot.send_message(
                    chat_id,
                    "Квиз завершен.",
                    reply_markup=get_main_menu_keyboard()
                )
            
            del quiz_states[chat_id]
            return
        
        question = questions[current_index]
        
        # Форматируем вопрос
        from utils.visual_helpers import format_quiz_question
        formatted_question = format_quiz_question(current_index + 1, len(questions), question['word'], question['options'])
        
        # Создаем клавиатуру с вариантами ответов
        from keyboards.submenus import quiz_keyboard
        keyboard = quiz_keyboard(question['options'], current_index)
        
        await bot.send_message(
            chat_id, 
            formatted_question,
            parse_mode="Markdown", 
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке вопроса квиза пользователю {chat_id}: {e}")
        await bot.send_message(chat_id, "Произошла ошибка при отправке вопроса. Пожалуйста, попробуйте позже.")

async def process_quiz_answer(callback: types.CallbackQuery, bot: Bot):
    """Обрабатывает ответ на вопрос квиза."""
    chat_id = callback.from_user.id
    
    try:
        # Обработка возврата и остановки
        if callback.data == "quiz:back":
            from keyboards.main_menu import main_menu_keyboard
            await bot.send_message(chat_id, "", reply_markup=main_menu_keyboard())
            if chat_id in quiz_states:
                del quiz_states[chat_id]
            await callback.answer()
            return
            
        if callback.data == "quiz:stop":
            from keyboards.main_menu import main_menu_keyboard
            await bot.send_message(chat_id, "Квиз остановлен.", reply_markup=main_menu_keyboard())
            if chat_id in quiz_states:
                del quiz_states[chat_id]
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
        
        state = quiz_states.get(chat_id)
        if not state:
            await callback.answer("Квиз не найден.", show_alert=True)
            return
            
        if q_index != state["current_index"]:
            await callback.answer("Неверная последовательность вопросов.", show_alert=True)
            return
            
        question = state["questions"][q_index]
        is_revision = state.get("is_revision", False)
        
        # Проверяем ответ
        if option_index == question["correct_index"]:
            # Правильный ответ
            try:
                # Явный импорт crud
                from database import crud
                
                # Получаем слово для добавления в словарь
                word_to_learn = extract_english(question["word"]).lower()
                
                # Улучшенная логика проверки и добавления слова
                current_learned = crud.get_learned_words(chat_id)
                current_learned_words = set(extract_english(word).lower() for word, _ in current_learned)
                
                # Добавляем слово в словарь только в обычном режиме и если еще не выучено
                if not is_revision and word_to_learn not in current_learned_words:
                    crud.add_learned_word(chat_id, question["word"], question["correct"], datetime.now().strftime("%Y-%m-%d"))
                    await callback.answer("Правильно! Слово добавлено в словарь.")
                elif is_revision:
                    await callback.answer("Правильно! (Режим повторения: слово уже в словаре)")
                else:
                    await callback.answer("Правильно! (Слово уже в словаре)")
                    
                state["correct"] += 1
            except Exception as e:
                logger.error(f"Ошибка при обработке правильного ответа для пользователя {chat_id}: {e}")
                await callback.answer("Правильно, но возникла ошибка при сохранении результата.")
        else:
            # Неправильный ответ
            await callback.answer(f"Неправильно! Правильный ответ: {question['correct']}")
            
        # Переходим к следующему вопросу
        state["current_index"] += 1
        await send_quiz_question(chat_id, bot)
    except ValueError as e:
        logger.error(f"Ошибка значения при обработке ответа на квиз: {e}")
        await callback.answer("Ошибка в формате данных ответа.")
    except Exception as e:
        logger.error(f"Ошибка при обработке ответа на квиз: {e}")
        await callback.answer("Произошла ошибка при обработке ответа.")

def register_quiz_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(
        lambda c: start_quiz(c, bot),
        lambda c: c.data == "quiz:start"
    )
    dp.register_callback_query_handler(
        lambda c: process_quiz_answer(c, bot),
        lambda c: c.data and c.data.startswith("quiz:")
    )

async def finish_level_test(chat_id: int, bot: Bot):
    """Updated to use improved result formatting and show main menu after sticker"""
    state = level_test_states.get(chat_id)
    if not state:
        return
    
    results = state["results"]
    
    # Group results by level
    results_by_level = {}
    for i, question in enumerate(state["questions"]):
        level = question["level"]
        if level not in results_by_level:
            results_by_level[level] = [0, 0]  # [correct, total]
        
        results_by_level[level][1] += 1
        if results[i]:
            results_by_level[level][0] += 1
    
    # Determine new level
    new_level = "A1"
    for level in LEVELS:
        score, total = results_by_level.get(level, [0, 0])
        if total > 0 and score >= 2:
            new_level = level
        else:
            break

    # Получаем текущий выбранный сет пользователя из базы и из кэша
    current_set = None

    # Проверяем сет в кэше
    try:
        from handlers.settings import user_set_selection
        if chat_id in user_set_selection:
            current_set = user_set_selection[chat_id]
    except ImportError:
        logger.error("Could not import user_set_selection, unable to preserve chosen set")

    # Если нет в кэше, смотрим в базе данных
    user = crud.get_user(chat_id)
    if not current_set and user and len(user) > 6:
        current_set = user[6]

    # Update user level in database
    crud.update_user_level(chat_id, new_level)
    
    # Если сет все еще не выбран, устанавливаем базовый для нового уровня
    if not current_set:
        from config import DEFAULT_SETS
        current_set = DEFAULT_SETS.get(new_level)
        if current_set:
            # Обновляем базу данных и кэш
            crud.update_user_chosen_set(chat_id, current_set)
            try:
                from handlers.settings import user_set_selection
                user_set_selection[chat_id] = current_set
            except ImportError:
                logger.error("Could not import user_set_selection, unable to update chosen set in memory")

    # Сбрасываем кэш ежедневных слов
    reset_daily_words_cache(chat_id)

    # Use the visual helper to format the results
    formatted_results = format_level_test_results(results_by_level, new_level)
    
    # Send results message first
    await bot.send_message(
        chat_id, 
        formatted_results,
        parse_mode="Markdown"
    )
    
    # Send sticker and show main menu
    from utils.sticker_helper import send_sticker_with_menu, get_congratulation_sticker
    await send_sticker_with_menu(chat_id, bot, get_congratulation_sticker())
    
    # Add the reply keyboard for commands
    from keyboards.reply_keyboards import get_main_menu_keyboard
    await bot.send_message(
        chat_id,
        "Используйте команды ниже или нажмите на кнопки основного меню:",
        reply_markup=get_main_menu_keyboard()
    )
    
    del level_test_states[chat_id]