import random
from datetime import datetime
from aiogram import types, Dispatcher, Bot
import asyncio
from database import crud
from utils.quiz_helpers import load_quiz_data
from keyboards.submenus import quiz_keyboard
from utils.helpers import get_daily_words_for_user, daily_words_cache
from config import REMINDER_START, DURATION_HOURS

# Глобальный словарь для хранения состояния квиза для каждого пользователя
quiz_states = {}

def extract_english(word_line: str) -> str:
    if " - " in word_line:
        return word_line.split(" - ", 1)[0].strip()
    return word_line.strip()

def generate_quiz_questions_from_daily(daily_words, level, chosen_set=None):
    quiz_data = load_quiz_data(level, chosen_set)
    if not quiz_data:
        return []
    mapping = { item["word"].lower(): item["translation"] for item in quiz_data }
    questions = []
    for word in daily_words:
        word_lc = word.lower()
        if word_lc not in mapping:
            continue
        correct_translation = mapping[word_lc]
        pool = [d["translation"] for d in quiz_data if d["translation"] != correct_translation]
        if len(pool) >= 3:
            distractors = random.sample(pool, 3)
        else:
            distractors = random.choices(pool, k=3)
        options = [correct_translation] + distractors
        random.shuffle(options)
        correct_index = options.index(correct_translation)
        questions.append({
            "word": word,
            "correct": correct_translation,
            "options": options,
            "correct_index": correct_index
        })
    return questions

async def start_quiz(callback: types.CallbackQuery, bot: Bot):
    chat_id = callback.from_user.id
    user = crud.get_user(chat_id)
    if not user:
        await bot.send_message(chat_id, "Профиль не найден. Используйте /start.")
        return
    level = user[1]
    # Получаем выбранный сет, если он есть
    from handlers.settings import user_set_selection
    chosen_set = user_set_selection.get(chat_id)
    
    # Получаем слова дня с учётом выбранного сета (кэш обновляется, если выбран новый сет)
    result = get_daily_words_for_user(chat_id, level, user[2], user[3],
                                       first_time=REMINDER_START, duration_hours=DURATION_HOURS, chosen_set=chosen_set)
    if result is None:
        await bot.send_message(chat_id, "Нет слов для квиза.")
        return
    # Получаем запись из кэша
    daily_entry = daily_words_cache[chat_id]
    raw_words = [msg.replace("🔹 ", "").strip() for msg in daily_entry[1]]
    daily_words = set(extract_english(line) for line in raw_words)
    learned = set(word for word, _ in crud.get_learned_words(chat_id))
    filtered_words = daily_words - learned
    if not filtered_words:
        await bot.send_message(chat_id, "Все слова из раздела 'Слова дня' уже выучены.")
        return
    questions = generate_quiz_questions_from_daily(list(filtered_words), level, chosen_set)
    if not questions:
        await bot.send_message(chat_id, "Нет данных для квиза.")
        return
    quiz_states[chat_id] = {"questions": questions, "current_index": 0, "correct": 0}
    await send_quiz_question(chat_id, bot)
    await callback.answer()

async def send_quiz_question(chat_id, bot: Bot):
    state = quiz_states.get(chat_id)
    if not state:
        return
    current_index = state["current_index"]
    questions = state["questions"]
    if current_index >= len(questions):
        await bot.send_message(chat_id, f"Квиз завершён! Правильных ответов: {state['correct']} из {len(questions)}.")
        del quiz_states[chat_id]
        return
    question = questions[current_index]
    text = f"Вопрос {current_index+1}:\nКакой перевод слова '{question['word']}'?"
    keyboard = quiz_keyboard(question['options'], current_index)
    await bot.send_message(chat_id, text, reply_markup=keyboard)

async def process_quiz_answer(callback: types.CallbackQuery, bot: Bot):
    if callback.data == "quiz:back":
        from keyboards.main_menu import main_menu_keyboard
        await bot.send_message(callback.from_user.id, "Главное меню", reply_markup=main_menu_keyboard())
        if callback.from_user.id in quiz_states:
            del quiz_states[callback.from_user.id]
        await callback.answer()
        return
    if callback.data == "quiz:stop":
        from keyboards.main_menu import main_menu_keyboard
        await bot.send_message(callback.from_user.id, "Квиз остановлен.", reply_markup=main_menu_keyboard())
        if callback.from_user.id in quiz_states:
            del quiz_states[callback.from_user.id]
        await callback.answer()
        return

    data = callback.data.split(":")
    if len(data) != 4:
        await callback.answer("Неверный формат данных.", show_alert=True)
        return
    _, _, q_index_str, option_index_str = data
    try:
        q_index = int(q_index_str)
        option_index = int(option_index_str)
    except ValueError:
        await callback.answer("Неверный формат данных.", show_alert=True)
        return
    chat_id = callback.from_user.id
    state = quiz_states.get(chat_id)
    if not state:
        await callback.answer("Квиз не найден.", show_alert=True)
        return
    if q_index != state["current_index"]:
        await callback.answer("Неверная последовательность вопросов.", show_alert=True)
        return
    question = state["questions"][q_index]
    if option_index == question["correct_index"]:
        crud.add_learned_word(chat_id, question["word"], question["correct"], datetime.now().strftime("%Y-%m-%d"))
        state["correct"] += 1
        await callback.answer("Правильно!")
    else:
        await callback.answer(f"Неправильно! Правильный ответ: {question['correct']}")
    state["current_index"] += 1
    await send_quiz_question(chat_id, bot)

def register_quiz_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(
        lambda c: start_quiz(c, bot),
        lambda c: c.data == "quiz:start"
    )
    dp.register_callback_query_handler(
        lambda c: process_quiz_answer(c, bot),
        lambda c: c.data and c.data.startswith("quiz:")
    )
