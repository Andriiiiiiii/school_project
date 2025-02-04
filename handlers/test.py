# handlers/test.py
import random
from aiogram import types, Dispatcher, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.helpers import load_words_for_level
from utils.constants import levels_order
from database import crud

# Глобальный словарь для хранения состояния теста уровня
test_sessions = {}

async def start_test(chat_id: int, bot: Bot):
    # Для теста берём 10 слов из файла, соответствующего текущему уровню пользователя
    proficiency = crud.get_user_proficiency(chat_id) or "A1"
    words = load_words_for_level(proficiency)
    if not words or len(words) < 10:
        # Если слов меньше 10, берём все
        test_words = words
    else:
        test_words = random.sample(words, 10)
    test_sessions[chat_id] = {
        'words': test_words,
        'index': 0,
        'correct': 0,
        'level': proficiency
    }
    await bot.send_message(chat_id, f"Начинаем тест уровня {proficiency}.")
    await send_test_question(chat_id, bot)

async def send_test_question(chat_id: int, bot: Bot):
    session = test_sessions.get(chat_id)
    if not session:
        return
    if session['index'] >= len(session['words']):
        # Тест завершён – выводим результат
        score = session['correct']
        await bot.send_message(chat_id, f"Тест завершён. Ваш результат: {score} из {len(session['words'])}.")
        del test_sessions[chat_id]
        return
    word = session['words'][session['index']]
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Знаю", callback_data="test:know"),
        InlineKeyboardButton("Не знаю", callback_data="test:donot")
    )
    await bot.send_message(chat_id, f"Знаете ли вы слово: {word}?", reply_markup=keyboard)

async def process_test_answer(callback_query: types.CallbackQuery, bot: Bot):
    chat_id = callback_query.from_user.id
    answer = callback_query.data.split(":")[1]
    session = test_sessions.get(chat_id)
    if not session:
        await bot.send_message(chat_id, "Тест не запущен. Используйте /test.")
        await callback_query.answer()
        return
    if answer == "know":
        session['correct'] += 1
    session['index'] += 1
    await callback_query.answer()
    await send_test_question(chat_id, bot)

def register_test_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(lambda c: c.data.startswith("test:"), lambda c: process_test_answer(c, bot))
    dp.register_callback_query_handler(lambda c: c.data == "menu:test", lambda c: start_test(c.from_user.id, bot))
    dp.register_message_handler(lambda m: start_test(m.chat.id, bot), commands=["test"])
