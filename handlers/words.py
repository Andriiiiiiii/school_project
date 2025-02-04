# handlers/words.py
import random
import os
import tempfile
import logging
from datetime import datetime

from aiogram import types, Dispatcher, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from gtts import gTTS

from database import crud
from utils.helpers import load_words_for_level
from utils.constants import levels_order

# Глобальные переменные для состояния теста и викторины
test_states = {}
quiz_data = {}

async def send_proficiency_word_of_day(chat_id: int, bot: Bot):
    proficiency = crud.get_user_proficiency(chat_id)
    if not proficiency:
        proficiency = "A1"
    try:
        current_index = levels_order.index(proficiency)
    except ValueError:
        current_index = 0
    next_index = current_index + 1 if current_index < len(levels_order) - 1 else current_index
    next_level = levels_order[next_index]
    words = load_words_for_level(next_level)
    if not words:
        await bot.send_message(chat_id, f"Файл для уровня {next_level} не найден или пуст.")
        return
    word = random.choice(words)
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔊 Послушать", callback_data=f"pronounce:{word}"),
        InlineKeyboardButton("📚 Добавить в словарь", callback_data=f"add:{word}")
    )
    await bot.send_message(chat_id, f"Слово дня (уровень {next_level}): {word}", reply_markup=keyboard)

async def start_test(chat_id: int, bot: Bot):
    initial_level = "A1"
    words = load_words_for_level(initial_level)
    if not words:
        await bot.send_message(chat_id, f"Файл для уровня {initial_level} не найден или пуст.")
        return
    test_states[chat_id] = {
        'current_level': initial_level,
        'words': words,
        'index': 0,
        'batch_size': 5
    }
    await bot.send_message(chat_id, f"Начинаем тест уровня. Уровень: {initial_level}")
    await send_test_question(chat_id, bot)

async def send_test_question(chat_id: int, bot: Bot):
    state = test_states.get(chat_id)
    if not state:
        return
    if state['index'] >= state['batch_size']:
        await bot.send_message(chat_id, "Вопросы закончились. Тест завершён.")
        del test_states[chat_id]
        return
    word = state['words'][state['index']]
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Знаю", callback_data="test:know"),
        InlineKeyboardButton("Не знаю", callback_data="test:donot")
    )
    await bot.send_message(chat_id, f"Знаете ли вы слово: {word}?", reply_markup=keyboard)

async def process_test_answer(callback_query: types.CallbackQuery, bot: Bot):
    chat_id = callback_query.from_user.id
    answer = callback_query.data.split(":")[1]  # "know" или "donot"
    state = test_states.get(chat_id)
    if not state:
        await bot.send_message(chat_id, "Тест не запущен. Используйте команду /test для начала.")
        await callback_query.answer()
        return
    current_level = state['current_level']
    if answer == "donot":
        crud.update_user_proficiency(chat_id, current_level)
        await bot.send_message(chat_id, f"Тест завершён. Ваш уровень: {current_level}")
        del test_states[chat_id]
    else:
        state['index'] += 1
        if state['index'] >= state['batch_size']:
            current_index = levels_order.index(current_level)
            if current_index < len(levels_order) - 1:
                new_level = levels_order[current_index + 1]
                state['current_level'] = new_level
                await bot.send_message(chat_id, f"Поздравляем! Вы прошли уровень {current_level}. Переход на уровень {new_level}.")
                words = load_words_for_level(new_level)
                state['words'] = words
                state['index'] = 0
            else:
                crud.update_user_proficiency(chat_id, current_level)
                await bot.send_message(chat_id, f"Тест завершён. Ваш уровень: {current_level}")
                del test_states[chat_id]
                await callback_query.answer()
                return
        await send_test_question(chat_id, bot)
    await callback_query.answer()

async def process_pronounce(callback_query: types.CallbackQuery, bot: Bot):
    word = callback_query.data.split(":")[1]
    chat_id = callback_query.from_user.id
    try:
        tts = gTTS(text=word, lang='en')
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tf:
            temp_filename = tf.name
            tts.save(temp_filename)
        with open(temp_filename, 'rb') as audio:
            await bot.send_audio(chat_id, audio, caption=f"Произношение: {word}")
    except Exception as e:
        logging.exception("Ошибка при генерации произношения")
        await bot.send_message(chat_id, "Не удалось сгенерировать произношение.")
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
    await callback_query.answer()

async def process_add_word(callback_query: types.CallbackQuery, bot: Bot):
    word = callback_query.data.split(":")[1]
    chat_id = callback_query.from_user.id
    # Здесь можно вызывать CRUD-функцию для сохранения слова
    await bot.send_message(chat_id, f"Слово '{word}' добавлено в словарь!")
    await callback_query.answer()

def register_words_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(lambda c: c.data.startswith("pronounce:"), lambda c: process_pronounce(c, bot))
    dp.register_callback_query_handler(lambda c: c.data.startswith("add:"), lambda c: process_add_word(c, bot))
    dp.register_callback_query_handler(lambda c: c.data.startswith("test:"), lambda c: process_test_answer(c, bot))
    dp.register_message_handler(lambda message: start_test(message.chat.id, bot), commands=["test"])
