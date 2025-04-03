# handlers/quiz.py
import random
from datetime import datetime
from aiogram import types, Dispatcher, Bot
import asyncio
from database import crud
from utils.quiz_helpers import load_quiz_data
from keyboards.submenus import quiz_keyboard
from utils.helpers import get_daily_words_for_user, daily_words_cache, extract_english
from config import REMINDER_START, DURATION_HOURS
import logging

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
        if word_lc not in mapping:
            continue
        
        correct_translation = mapping[word_lc]
        
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
    Инициализирует квиз для пользователя.
    """
    chat_id = callback.from_user.id
    try:
        user = crud.get_user(chat_id)
        if not user:
            await bot.send_message(chat_id, "Профиль не найден. Используйте /start.")
            return
        level = user[1]
        
        # Получаем выбранный сет, если он есть
        try:
            from handlers.settings import user_set_selection
            chosen_set = user_set_selection.get(chat_id)
        except ImportError:
            logger.error("Error importing user_set_selection, using default set")
            chosen_set = None
        
        # Получаем слова дня
        try:
            result = get_daily_words_for_user(chat_id, level, user[2], user[3],
                                           first_time=REMINDER_START, duration_hours=DURATION_HOURS, chosen_set=chosen_set)
            if result is None:
                await bot.send_message(chat_id, "Нет слов для квиза.")
                return
                
            # Получаем запись из кэша
            if chat_id not in daily_words_cache:
                logger.error(f"Cache miss for user {chat_id}")
                await bot.send_message(chat_id, "Ошибка при получении слов дня. Пожалуйста, попробуйте позже.")
                return
                
            daily_entry = daily_words_cache[chat_id]
            raw_words = [msg.replace("🔹 ", "").strip() for msg in daily_entry[1]]
            
            # Удаляем возможное префиксное сообщение (начинается с "🎓", "⚠️" и др.)
            if raw_words and (raw_words[0].startswith("🎓") or raw_words[0].startswith("⚠️")):
                raw_words = raw_words[1:]
                
            daily_words = set(extract_english(line) for line in raw_words)
            
            # Определяем, находимся ли мы в режиме повторения
            is_revision_mode = len(daily_entry) > 9 and daily_entry[9]
            
            # Если режим повторения, нам не нужно фильтровать выученные слова
            if not is_revision_mode:
                # Получаем выученные слова только в обычном режиме
                try:
                    learned = set(word for word, _ in crud.get_learned_words(chat_id))
                except Exception as e:
                    logger.error(f"Error getting learned words for user {chat_id}: {e}")
                    learned = set()
                    
                filtered_words = daily_words - learned
                
                if not filtered_words:
                    # Особое сообщение если все слова дня уже выучены, но мы не в режиме повторения
                    await bot.send_message(chat_id, "Все слова из раздела 'Слова дня' уже выучены! Попробуйте завтра или выберите новый набор слов.")
                    return
                    
                quiz_words = list(filtered_words)
            else:
                # В режиме повторения используем все слова дня
                quiz_words = list(daily_words)
                
            # Генерируем вопросы для квиза с учетом режима повторения
            questions = generate_quiz_questions_from_daily(quiz_words, level, chosen_set, is_revision_mode)
            if not questions:
                if is_revision_mode:
                    await bot.send_message(chat_id, "Не удалось создать вопросы для повторения. Попробуйте выбрать другой набор слов.")
                else:
                    await bot.send_message(chat_id, "Нет данных для квиза. Возможно, все слова уже выучены.")
                return
                
            # Сохраняем состояние квиза, включая информацию о режиме повторения
            quiz_states[chat_id] = {"questions": questions, "current_index": 0, "correct": 0, "is_revision": is_revision_mode}
            
            # Добавляем информативное сообщение перед началом квиза
            if is_revision_mode:
                await bot.send_message(chat_id, "📝 Режим повторения: слова уже добавлены в Ваш словарь.")
                
            await send_quiz_question(chat_id, bot)
        except KeyError as e:
            logger.error(f"Cache error for user {chat_id}: {e}")
            await bot.send_message(chat_id, "Ошибка при получении слов дня. Пожалуйста, попробуйте позже.")
        except Exception as e:
            logger.error(f"Error setting up quiz for user {chat_id}: {e}")
            await bot.send_message(chat_id, "Произошла ошибка при настройке квиза. Пожалуйста, попробуйте позже.")
    except Exception as e:
        logger.error(f"Unhandled error in start_quiz for user {chat_id}: {e}")
        await bot.send_message(chat_id, "Произошла неожиданная ошибка. Пожалуйста, попробуйте позже.")
    
    await callback.answer()

async def send_quiz_question(chat_id, bot: Bot):
    try:
        state = quiz_states.get(chat_id)
        if not state:
            return
        current_index = state["current_index"]
        questions = state["questions"]
        is_revision = state.get("is_revision", False)
        
        if current_index >= len(questions):
            # Квиз завершен
            from keyboards.main_menu import main_menu_keyboard
            
            # Формируем сообщение с результатами
            result_message = f"Квиз завершён! Правильных ответов: {state['correct']} из {len(questions)}."
            
            # Добавляем информацию о дальнейших действиях
            if is_revision:
                result_message += "\n\nРежим повторения: вы уже изучили все слова в этом наборе."
                result_message += "\nПопробуйте выбрать другой набор слов или перейти на следующий уровень."
            
            # Создаем клавиатуру с дополнительными вариантами
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("Главное меню", callback_data="menu:back"))
            
            if is_revision:
                keyboard.add(types.InlineKeyboardButton("Выбрать новый набор", callback_data="settings:set"))
                keyboard.add(types.InlineKeyboardButton("Пройти тест уровня", callback_data="test_level:start"))
            
            await bot.send_message(chat_id, result_message, reply_markup=keyboard)
            del quiz_states[chat_id]
            return
            
        # Отправка очередного вопроса
        question = questions[current_index]
        text = f"Вопрос {current_index+1}:\nКакой перевод слова '{question['word']}'?"
        
        # Добавляем информацию о режиме, если это режим повторения
        if is_revision:
            text = "🔄 ПОВТОРЕНИЕ\n" + text
            
        keyboard = quiz_keyboard(question['options'], current_index)
        await bot.send_message(chat_id, text, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error sending quiz question to user {chat_id}: {e}")
        await bot.send_message(chat_id, "Произошла ошибка при отправке вопроса. Пожалуйста, попробуйте позже.")

async def process_quiz_answer(callback: types.CallbackQuery, bot: Bot):
    chat_id = callback.from_user.id
    
    try:
        if callback.data == "quiz:back":
            from keyboards.main_menu import main_menu_keyboard
            await bot.send_message(chat_id, "Главное меню", reply_markup=main_menu_keyboard())
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
        
        if option_index == question["correct_index"]:
            # Правильный ответ
            try:
                # Добавляем слово в изученные только если не находимся в режиме повторения
                if not is_revision:
                    crud.add_learned_word(chat_id, question["word"], question["correct"], datetime.now().strftime("%Y-%m-%d"))
                    await callback.answer("Правильно! Слово добавлено в словарь.")
                else:
                    # В режиме повторения не сохраняем слово повторно
                    await callback.answer("Правильно! (Слово уже в вашем словаре)")
                state["correct"] += 1
            except Exception as e:
                logger.error(f"Error adding learned word for user {chat_id}: {e}")
                await callback.answer("Правильно, но возникла ошибка при сохранении результата.")
        else:
            # Неправильный ответ
            await callback.answer(f"Неправильно! Правильный ответ: {question['correct']}")
            
        state["current_index"] += 1
        await send_quiz_question(chat_id, bot)
    except ValueError as e:
        logger.error(f"Value error processing quiz answer: {e}")
        await callback.answer("Ошибка в формате данных ответа.")
    except Exception as e:
        logger.error(f"Error processing quiz answer: {e}")
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