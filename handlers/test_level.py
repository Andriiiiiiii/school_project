# handlers/test_level.py
import os
import random
from aiogram import types, Dispatcher, Bot
from database import crud

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
    """
    try:
        questions = []
        for level in LEVELS:
            try:
                words = load_words_for_level_file(level)
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
                        # Выбираем ложные варианты из того же файла, исключая правильный
                        distractor_pool = [w["translation"] for w in words if w["translation"] != correct]
                        
                        if len(distractor_pool) >= 3:
                            distractors = random.sample(distractor_pool, 3)
                        else:
                            distractors = distractor_pool  # если меньше 3, используем имеющиеся
                            # Если не хватает, добавляем случайные строки
                            while len(distractors) < 3:
                                distractors.append(f"Вариант {len(distractors) + 1}")
                                
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
    """
    Генерирует тестовые вопросы для каждого уровня.
    Для каждого уровня из LEVELS выбирается 3 случайных слова (если доступно).
    Для каждого слова генерируются 5 вариантов ответа:
      - Правильный перевод.
      - Три ложных перевода, выбранных из того же уровня.
      - Фиксированная опция "Не знаю" (всегда последняя).
    Возвращает список вопросов, каждый вопрос – словарь:
      {
         "level": <уровень>,
         "word": <английское слово>,
         "correct": <правильный перевод>,
         "options": [вариант1, вариант2, вариант3, вариант4, "Не знаю"],
         "correct_index": <индекс правильного ответа среди первых 4 вариантов>
      }
    """
    questions = []
    for level in LEVELS:
        words = load_words_for_level_file(level)
        if not words:
            continue
        # Если в файле меньше 3 слова, выбираем все; иначе случайно выбираем 3 слова
        if len(words) < 3:
            selected = words
        else:
            selected = random.sample(words, 3)
        for entry in selected:
            correct = entry["translation"]
            # Выбираем ложные варианты из того же файла, исключая правильный
            distractor_pool = [w["translation"] for w in words if w["translation"] != correct]
            if len(distractor_pool) >= 3:
                distractors = random.sample(distractor_pool, 3)
            else:
                distractors = distractor_pool  # если меньше 3, используем имеющиеся
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
    # Сортируем вопросы по порядку уровней (блоками: сначала A1, затем A2 и т.д.)
    def level_order(q):
        try:
            return LEVELS.index(q["level"])
        except ValueError:
            return 999
    questions.sort(key=level_order)
    return questions

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
    """
    Отправляет следующий вопрос теста пользователю.
    Если вопросов больше нет, завершает тест и обрабатывает результаты.
    Формирует клавиатуру с вариантами ответов в два столбца:
      - Ряд 1: варианты 1 и 2
      - Ряд 2: варианты 3 и 4
      - Ряд 3: вариант "Не знаю" и кнопка "Остановить тест"
    """
    state = level_test_states.get(chat_id)
    if not state:
        return
    if state["current_index"] >= len(state["questions"]):
        await finish_level_test(chat_id, bot)
        return
    question = state["questions"][state["current_index"]]
    text = f"Вопрос {state['current_index'] + 1} (Уровень {question['level']}):\nКакой перевод слова «{question['word']}»?"
    
    # Создаем клавиатуру с двумя столбцами
    keyboard = types.InlineKeyboardMarkup()
    # Первые две кнопки (варианты с индексами 0 и 1)
    row1 = [
        types.InlineKeyboardButton(question["options"][0], callback_data=f"lvltest:{state['current_index']}:{0}"),
        types.InlineKeyboardButton(question["options"][1], callback_data=f"lvltest:{state['current_index']}:{1}")
    ]
    # Следующие две кнопки (варианты с индексами 2 и 3)
    row2 = [
        types.InlineKeyboardButton(question["options"][2], callback_data=f"lvltest:{state['current_index']}:{2}"),
        types.InlineKeyboardButton(question["options"][3], callback_data=f"lvltest:{state['current_index']}:{3}")
    ]
    # Последняя строка: вариант "Не знаю" (индекс 4) и кнопка "Остановить тест"
    row3 = [
        types.InlineKeyboardButton(question["options"][4], callback_data=f"lvltest:{state['current_index']}:{4}"),
        types.InlineKeyboardButton("Остановить тест", callback_data="lvltest:stop")
    ]
    keyboard.row(*row1)
    keyboard.row(*row2)
    keyboard.row(*row3)
    
    await bot.send_message(chat_id, text, reply_markup=keyboard)

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
    """
    Завершает тест:
    - Группирует результаты по уровням.
    - Для каждого уровня, если пользователь ответил правильно на минимум 2 из 3 вопросов,
      блок считается пройденным.
    - Новый уровень определяется как уровень последнего успешно пройденного блока.
    - Обновляет уровень пользователя в БД и отправляет сводку.
    Добавляется кнопка "Главное меню" для возврата.
    """
    state = level_test_states.get(chat_id)
    if not state:
        return
    results = state["results"]
    # Подсчитываем результаты для каждого уровня (блок)
    block_scores = {level: 0 for level in LEVELS}
    block_counts = {level: 0 for level in LEVELS}
    for i, question in enumerate(state["questions"]):
        level = question["level"]
        block_counts[level] += 1
        if results[i]:
            block_scores[level] += 1
    new_level = "A1"
    # Определяем новый уровень: каждый уровень считается пройденным, если верных ответов ≥2 из 3
    for level in LEVELS:
        if block_counts[level] > 0 and block_scores[level] >= 2:
            new_level = level
        else:
            break
    # Обновляем уровень пользователя в БД
    crud.update_user_level(chat_id, new_level)
    summary = "Тест завершён!\nРезультаты по уровням:\n"
    for level in LEVELS:
        if block_counts[level] > 0:
            summary += f"{level}: {block_scores[level]} из {block_counts[level]}\n"
    summary += f"\nВаш новый уровень: {new_level}"
    # Создаем клавиатуру с кнопкой "Главное меню"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Главное меню", callback_data="menu:back"))
    await bot.send_message(chat_id, summary, reply_markup=keyboard)
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
