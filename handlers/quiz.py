# handlers/quiz.py
import random
from datetime import datetime
from aiogram import types, Dispatcher, Bot
import asyncio
from database import crud
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
    """Инициализирует квиз для пользователя."""
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
            logger.error("Ошибка импорта user_set_selection, используем набор по умолчанию")
            chosen_set = None
        
        # Получаем список уже выученных слов из БД
        try:
            learned_raw = crud.get_learned_words(chat_id)
            learned_set = set(extract_english(item[0]).lower() for item in learned_raw)
            logger.info(f"У пользователя {chat_id} есть {len(learned_set)} выученных слов")
        except Exception as e:
            logger.error(f"Ошибка получения выученных слов для пользователя {chat_id}: {e}")
            learned_set = set()
        
        # Получаем слова дня
        try:
            result = get_daily_words_for_user(chat_id, level, user[2], user[3],
                                           first_time=REMINDER_START, duration_hours=DURATION_HOURS, chosen_set=chosen_set)
            if result is None:
                await bot.send_message(chat_id, "Нет слов для квиза.")
                return
                
            # Получаем запись из кэша
            if chat_id not in daily_words_cache:
                logger.error(f"Кэш не найден для пользователя {chat_id}")
                await bot.send_message(chat_id, "Ошибка при получении слов дня. Пожалуйста, попробуйте позже.")
                return
                
            daily_entry = daily_words_cache[chat_id]
            raw_words = [msg.replace("🔹 ", "").strip() for msg in daily_entry[1]]
            
            # Удаляем возможное префиксное сообщение
            if raw_words and (raw_words[0].startswith("🎓") or raw_words[0].startswith("⚠️")):
                raw_words = raw_words[1:]
                
            # Извлекаем английские слова и приводим к нижнему регистру
            daily_words = [extract_english(line).lower() for line in raw_words]
            daily_words_set = set(daily_words)
            
            # Определяем режим повторения
            is_revision_mode = len(daily_entry) > 9 and daily_entry[9]
            logger.info(f"Пользователь {chat_id} в режиме повторения: {is_revision_mode}")
            
            # Фильтруем слова
            unlearned_words = daily_words_set - learned_set
            
            if not unlearned_words and not is_revision_mode:
                await bot.send_message(chat_id, "Все слова из раздела 'Слова дня' уже выучены! Попробуйте завтра или выберите новый набор слов.")
                return
            
            # Определяем, какие слова использовать в квизе
            if is_revision_mode:
                quiz_words = list(daily_words)
            else:
                quiz_words = list(unlearned_words)
                # Доп. проверка для безопасности
                if not quiz_words:
                    await bot.send_message(chat_id, "Нет данных для квиза. Возможно, все слова уже выучены.")
                    return
            
            logger.info(f"Подготовлено {len(quiz_words)} слов для квиза пользователя {chat_id}")
            
            # Генерируем вопросы для квиза
            questions = generate_quiz_questions_from_daily(quiz_words, level, chosen_set, is_revision_mode)
            
            if not questions:
                logger.warning(f"Не удалось создать вопросы для квиза из {len(quiz_words)} слов у пользователя {chat_id}")
                
                if is_revision_mode:
                    await bot.send_message(chat_id, "Не удалось создать вопросы для повторения. Попробуйте выбрать другой набор слов.")
                else:
                    await bot.send_message(chat_id, "Нет данных для квиза. Возможно, все слова уже выучены.")
                return
                
            # Сохраняем состояние квиза
            quiz_states[chat_id] = {"questions": questions, "current_index": 0, "correct": 0, "is_revision": is_revision_mode}
            
            # Информационное сообщение перед началом квиза
            if is_revision_mode:
                await bot.send_message(chat_id, "📝 *Режим повторения*: слова уже добавлены в Ваш словарь.", parse_mode="Markdown")
            else:
                await bot.send_message(chat_id, "📝 *Квиз по невыученным словам*: правильные ответы будут добавлены в Ваш словарь.", parse_mode="Markdown")
                
            await send_quiz_question(chat_id, bot)
            
        except Exception as e:
            logger.error(f"Ошибка при настройке квиза для пользователя {chat_id}: {e}")
            await bot.send_message(chat_id, "Произошла ошибка при настройке квиза. Пожалуйста, попробуйте позже.")
    except Exception as e:
        logger.error(f"Необработанная ошибка в start_quiz для пользователя {chat_id}: {e}")
        await bot.send_message(chat_id, "Произошла неожиданная ошибка. Пожалуйста, попробуйте позже.")
    
    await callback.answer()

# Остальной код оставляем без изменений
async def send_quiz_question(chat_id, bot: Bot):
    """Отправляет вопрос квиза."""
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
            result_message = format_result_message(
                state['correct'], 
                len(questions),
                is_revision
            )
            
            # Создаем клавиатуру
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("Главное меню", callback_data="menu:back"))
            
            if is_revision:
                keyboard.add(types.InlineKeyboardButton("Выбрать новый набор", callback_data="settings:set"))
                keyboard.add(types.InlineKeyboardButton("Пройти тест уровня", callback_data="test_level:start"))
            
            # Отправляем сообщение с результатами
            await bot.send_message(
                chat_id, 
                result_message,
                parse_mode="Markdown", 
                reply_markup=keyboard
            )
            
            # Отправляем стикер поздравления при хорошем результате
            if state['correct'] / len(questions) >= 0.7:
                sticker_id = get_congratulation_sticker()
                if sticker_id:
                    await bot.send_sticker(chat_id, sticker_id)
            
            del quiz_states[chat_id]
            return
            
        # Отправляем вопрос
        question = questions[current_index]
        
        # Форматируем вопрос
        formatted_question = format_quiz_question(
            current_index + 1,
            len(questions),
            question['word'],
            question['options'],
            is_revision
        )
        
        # Создаем клавиатуру с вариантами ответов
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


# Функция обработки ответа на вопрос квиза
async def process_quiz_answer(callback: types.CallbackQuery, bot: Bot):
    """Обрабатывает ответ на вопрос квиза."""
    chat_id = callback.from_user.id
    
    try:
        # Обработка возврата и остановки
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
                # Проверяем, не добавлено ли уже слово в выученные
                current_learned = crud.get_learned_words(chat_id)
                current_learned_words = set(extract_english(word).lower() for word, _ in current_learned)
                word_to_learn = extract_english(question["word"]).lower()
                
                # Добавляем слово только в обычном режиме и если еще не выучено
                if not is_revision and word_to_learn not in current_learned_words:
                    crud.add_learned_word(chat_id, question["word"], question["correct"], datetime.now().strftime("%Y-%m-%d"))
                    await callback.answer("Правильно! Слово добавлено в словарь.")
                elif is_revision:
                    await callback.answer("Правильно! (Слово уже в вашем словаре)")
                else:
                    await callback.answer("Правильно! (Слово уже было в вашем словаре)")
                    
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