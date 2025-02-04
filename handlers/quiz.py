# handlers/quiz.py
import random
from aiogram import types, Dispatcher, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import crud
from utils.helpers import load_words_for_level
from utils.constants import levels_order

# Глобальный словарь для хранения состояния викторины
quiz_sessions = {}

# Функция для старта викторины
async def start_quiz(chat_id: int, bot: Bot):
    # Для примера будем использовать слова из уровня, следующего за текущим
    proficiency = crud.get_user_proficiency(chat_id) or "A1"
    try:
        idx = levels_order.index(proficiency)
    except ValueError:
        idx = 0
    next_idx = idx + 1 if idx < len(levels_order) - 1 else idx
    level = levels_order[next_idx]
    words = load_words_for_level(level)
    if not words:
        await bot.send_message(chat_id, f"Нет слов для уровня {level}.")
        return
    # Выбираем 5 случайных слов для викторины
    quiz_words = random.sample(words, min(5, len(words)))
    # Сохраняем сессию: список слов и счетчик правильных ответов
    quiz_sessions[chat_id] = {
        'words': quiz_words,
        'index': 0,
        'score': 0,
        'level': level
    }
    await send_quiz_question(chat_id, bot)

# Функция отправки одного вопроса викторины
async def send_quiz_question(chat_id: int, bot: Bot):
    session = quiz_sessions.get(chat_id)
    if not session:
        return
    if session['index'] >= len(session['words']):
        # Если вопросы закончились, выводим результат
        score = session['score']
        await bot.send_message(chat_id, f"Викторина завершена! Ваш результат: {score} из {len(session['words'])}")
        del quiz_sessions[chat_id]
        return
    word = session['words'][session['index']]
    # Для примера создадим вопрос "Выберите правильный перевод" с фиктивными вариантами
    correct_translation = f"Перевод {word}"
    options = [correct_translation, f"Неверный 1", f"Неверный 2", f"Неверный 3"]
    random.shuffle(options)
    keyboard = InlineKeyboardMarkup(row_width=2)
    for opt in options:
        flag = "1" if opt == correct_translation else "0"
        keyboard.add(InlineKeyboardButton(opt, callback_data=f"quiz:{flag}"))
    await bot.send_message(chat_id, f"Как переводится слово '{word}'?", reply_markup=keyboard)

# Обработка ответа викторины
async def process_quiz_answer(callback_query: types.CallbackQuery, bot: Bot):
    chat_id = callback_query.from_user.id
    flag = callback_query.data.split(":")[1]
    session = quiz_sessions.get(chat_id)
    if not session:
        await bot.send_message(chat_id, "Викторина не запущена. Используйте /quiz.")
        await callback_query.answer()
        return
    if flag == "1":
        session['score'] += 1
    session['index'] += 1
    await callback_query.answer()
    await send_quiz_question(chat_id, bot)

def register_quiz_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(lambda c: c.data.startswith("quiz:"), lambda c: process_quiz_answer(c, bot))
    dp.register_callback_query_handler(lambda c: c.data == "menu:quiz", lambda c: start_quiz(c.from_user.id, bot))
    dp.register_message_handler(lambda m: start_quiz(m.chat.id, bot), commands=["quiz"])
