import random
from aiogram import types, Dispatcher, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.helpers import load_words_for_level
from utils.constants import levels_order
from database import crud

# Глобальный словарь для хранения состояния теста уровня
test_sessions = {}

async def start_test(chat_id: int, bot: Bot):
    proficiency = crud.get_user_proficiency(chat_id) or "A1"
    words = load_words_for_level(proficiency)

    if not words or len(words) < 10:
        test_words = words  # Если слов мало, берём все
    else:
        test_words = random.sample(words, 10)  # Берем 10 случайных

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

# Обёртка-обработчик для кнопки "Тест уровня" (callback_data="menu:test")
async def start_test_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()  # Убираем "часики" на кнопке
    await start_test(callback_query.from_user.id, callback_query.bot)

# Обёртка-обработчик для ответов "Знаю/Не знаю" (callback_data="test:...")
async def process_test_answer_callback(callback_query: types.CallbackQuery):
    await process_test_answer(callback_query, callback_query.bot)

# Обёртка-обработчик для команды /test
async def start_test_message_handler(message: types.Message):
    await start_test(message.chat.id, message.bot)

def register_test_handlers(dp: Dispatcher, bot: Bot):
    # Обработчик: если callback_data начинается с "test:", значит это ответ на вопрос
    dp.register_callback_query_handler(
        process_test_answer_callback,
        lambda c: c.data.startswith("test:")
    )

    # Обработчик: если callback_data == "menu:test", значит нажата кнопка "Тест уровня"
    dp.register_callback_query_handler(
        start_test_callback,
        lambda c: c.data == "menu:test"
    )

    # Обработчик для команды /test
    dp.register_message_handler(
        start_test_message_handler,
        commands=["test"]
    )
