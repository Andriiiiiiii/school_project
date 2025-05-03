# handlers/test_level.py
import os
import random
from aiogram import types, Dispatcher, Bot
from database import crud
import logging

# Import the visual helpers
from utils.visual_helpers import format_level_test_question, format_level_test_results


# Настройка логирования
logger = logging.getLogger(__name__)

# Глобальное хранилище состояния теста для каждого пользователя (ключ – chat_id)
level_test_states = {}

# Список уровней в порядке возрастания сложности
LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]

def load_words_for_level_file(level: str):
    """
    Загружает слова из файла levels/<level>.txt.
    Каждая строка должна иметь формат: "word - translation1, translation2, ..."
    """
    filename = os.path.join("levels", f"{level}.txt")
    words = []
    
    try:
        if not os.path.exists(filename):
            logger.warning(f"Level file not found: {filename}")
            return words
            
        with open(filename, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(" - ")
                if len(parts) < 2:
                    continue
                english = parts[0].strip()
                translation = parts[1].strip()
                words.append({"word": english, "translation": translation})
                
        logger.debug(f"Loaded {len(words)} words from level {level}")
        return words
    except FileNotFoundError:
        logger.error(f"Level file not found: {filename}")
        return words
    except PermissionError:
        logger.error(f"Permission denied when accessing level file: {filename}")
        return words
    except UnicodeDecodeError:
        logger.warning(f"Unicode decode error in file {filename}, trying with cp1251 encoding")
        try:
            with open(filename, encoding="cp1251") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(" - ")
                    if len(parts) < 2:
                        continue
                    english = parts[0].strip()
                    translation = parts[1].strip()
                    words.append({"word": english, "translation": translation})
            logger.debug(f"Loaded {len(words)} words from level {level} with cp1251 encoding")
            return words
        except Exception as e:
            logger.error(f"Failed to load file with alternative encoding: {e}")
            return words
    except Exception as e:
        logger.error(f"Error loading words from level {level}: {e}")
        return words

def generate_level_test_questions():
    """
    Генерирует тестовые вопросы для каждого уровня.
    Улучшенная версия, которая использует отвлекающие варианты из других уровней
    вместо искусственных надписей "Вариант N".
    """
    try:
        questions = []
        # Заранее загрузим слова для всех уровней для формирования пула отвлекающих вариантов
        all_words_by_level = {}
        all_translations = []
        
        for level in LEVELS:
            words = load_words_for_level_file(level)
            if words:
                all_words_by_level[level] = words
                # Сразу формируем общий пул переводов для отвлекающих вариантов
                all_translations.extend([w["translation"] for w in words])
        
        for level in LEVELS:
            try:
                words = all_words_by_level.get(level, [])
                if not words:
                    logger.warning(f"No words found for level {level}")
                    continue
                
                # Если в файле меньше 3 слова, выбираем все; иначе случайно выбираем 3 слова
                if len(words) < 3:
                    selected = words
                else:
                    selected = random.sample(words, 3)
                
                for entry in selected:
                    try:
                        correct = entry["translation"]
                        # Формируем пул отвлекающих вариантов из всех уровней, исключая правильный
                        distractor_pool = [t for t in all_translations if t != correct]
                        
                        if len(distractor_pool) >= 3:
                            # Если достаточно уникальных вариантов, выбираем без повторений
                            distractors = random.sample(distractor_pool, 3)
                        else:
                            # Если недостаточно вариантов, используем random.choices с возможными повторениями
                            # Это лучше, чем искусственные "Вариант N"
                            distractors = random.choices(distractor_pool, k=3) if distractor_pool else ["???", "???", "???"]
                        
                        # Перемешиваем первые 4 варианта (правильный + ложные)
                        options_temp = [correct] + distractors
                        random.shuffle(options_temp)
                        
                        # Правильный ответ содержится в options_temp; его индекс запоминаем
                        correct_index = options_temp.index(correct)
                        
                        # Добавляем фиксированную опцию "Не знаю" в конец
                        options = options_temp + ["Не знаю"]
                        
                        questions.append({
                            "level": level,
                            "word": entry["word"],
                            "correct": correct,
                            "options": options,
                            "correct_index": correct_index
                        })
                    except KeyError as e:
                        logger.error(f"Missing required key in word entry for level {level}: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing question for level {level}: {e}")
                        continue
            except Exception as e:
                logger.error(f"Error generating questions for level {level}: {e}")
                continue
        
        # Сортируем вопросы по порядку уровней
        def level_order(q):
            try:
                return LEVELS.index(q["level"])
            except ValueError:
                return 999
        questions.sort(key=level_order)
        
        logger.info(f"Generated {len(questions)} level test questions")
        return questions
    except Exception as e:
        logger.error(f"Error in generate_level_test_questions: {e}")
        return []

async def start_level_test(chat_id: int, bot: Bot):
    """
    Инициализирует тест для пользователя:
    - Генерирует вопросы (по 3 на каждый уровень, если данные доступны).
    - Сохраняет состояние теста в level_test_states.
    - Отправляет первый вопрос.
    """
    questions = generate_level_test_questions()
    if not questions:
        await bot.send_message(chat_id, "Нет данных для тестирования. Проверьте файлы уровней.")
        return
    level_test_states[chat_id] = {
        "questions": questions,
        "current_index": 0,
        "results": []  # Список True/False для каждого вопроса
    }
    await send_next_level_question(chat_id, bot)

async def send_next_level_question(chat_id: int, bot: Bot):
    """Send the next level test question with enhanced formatting"""
    state = level_test_states.get(chat_id)
    if not state:
        return
    
    if state["current_index"] >= len(state["questions"]):
        await finish_level_test(chat_id, bot)
        return
    
    question = state["questions"][state["current_index"]]
    
    # Use the visual helper to format the question
    formatted_question = format_level_test_question(
        state["current_index"],
        len(state["questions"]),
        question["level"],
        question["word"]
    )
    
    # Create keyboard with improved layout
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    # First two options
    row1 = [
        types.InlineKeyboardButton(question["options"][0], callback_data=f"lvltest:{state['current_index']}:{0}"),
        types.InlineKeyboardButton(question["options"][1], callback_data=f"lvltest:{state['current_index']}:{1}")
    ]
    
    # Next two options
    row2 = [
        types.InlineKeyboardButton(question["options"][2], callback_data=f"lvltest:{state['current_index']}:{2}"),
        types.InlineKeyboardButton(question["options"][3], callback_data=f"lvltest:{state['current_index']}:{3}")
    ]
    
    # "Don't know" and "Stop test" buttons
    row3 = [
        types.InlineKeyboardButton(question["options"][4], callback_data=f"lvltest:{state['current_index']}:{4}"),
        types.InlineKeyboardButton("⛔ Stop Test", callback_data="lvltest:stop")
    ]
    
    keyboard.row(*row1)
    keyboard.row(*row2)
    keyboard.row(*row3)
    
    await bot.send_message(
        chat_id, 
        formatted_question,
        parse_mode="Markdown", 
        reply_markup=keyboard
    )

async def handle_level_test_answer(callback: types.CallbackQuery, bot: Bot):
    """
    Обрабатывает ответ пользователя:
    - Если пользователь нажал "Остановить тест", тест завершается.
    - Иначе, сравнивает выбранный вариант с правильным,
      сохраняет результат и отправляет следующий вопрос.
    """
    if callback.data == "lvltest:stop":
        # Остановка теста
        await bot.send_message(callback.from_user.id, "Тест остановлен.")
        if callback.from_user.id in level_test_states:
            del level_test_states[callback.from_user.id]
        await callback.answer()
        return

    data = callback.data.split(":")
    if len(data) != 3:
        await callback.answer("Неверный формат данных.", show_alert=True)
        return
    _, q_index_str, option_index_str = data
    try:
        q_index = int(q_index_str)
        option_index = int(option_index_str)
    except ValueError:
        await callback.answer("Неверный формат данных.", show_alert=True)
        return
    chat_id = callback.from_user.id
    state = level_test_states.get(chat_id)
    if not state or q_index >= len(state["questions"]):
        await callback.answer("Тест не найден или завершён.", show_alert=True)
        return
    question = state["questions"][q_index]
    is_correct = (option_index == question["correct_index"])
    state["results"].append(is_correct)
    state["current_index"] += 1
    response_text = "Правильно!" if is_correct else f"Неправильно! Правильный ответ: {question['correct']}"
    await callback.answer(response_text)
    await send_next_level_question(chat_id, bot)

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
    from utils.helpers import reset_daily_words_cache
    reset_daily_words_cache(chat_id)

    # Use the visual helper to format the results
    from utils.visual_helpers import format_level_test_results
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
    
    # Add only main menu button
    from keyboards.reply_keyboards import get_main_menu_keyboard
    await bot.send_message(
        chat_id,
        "Тест уровня завершен.",
        reply_markup=get_main_menu_keyboard()
    )
    
    del level_test_states[chat_id]

def register_level_test_handlers(dp: Dispatcher, bot: Bot):
    """
    Регистрирует обработчики для нового теста:
      - Запуск теста по callback_data "test_level:start"
      - Обработка ответов с префиксом "lvltest:"
    """
    dp.register_callback_query_handler(
        lambda c: start_level_test(c.from_user.id, bot),
        lambda c: c.data == "test_level:start"
    )
    dp.register_callback_query_handler(
        lambda c: handle_level_test_answer(c, bot),
        lambda c: c.data and c.data.startswith("lvltest:")
    )