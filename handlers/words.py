# handlers/words.py
import random
import os
import tempfile
import logging
from aiogram import types, Dispatcher, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from gtts import gTTS
from database import crud
from utils.helpers import load_words_for_level
from utils.constants import levels_order

# Функция отправки слова дня с подробностями
async def send_word_of_day(chat_id: int, bot: Bot):
    # Определяем текущий уровень пользователя и выбираем слово из следующего уровня
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
        await bot.send_message(chat_id, f"Словарь для уровня {next_level} не найден или пуст.")
        return
    word = random.choice(words)
    # Формируем сообщение (здесь можно расширить получение транскрипции и перевода)
    text = f"Слово дня (уровень {next_level}):\n\n" \
           f"Слово: {word}\n" \
           f"Транскрипция: (пример транскрипции)\n" \
           f"Перевод: (пример перевода)\n" \
           f"Пример: (пример использования слова в предложении)"
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("📚 Добавить в словарь", callback_data=f"add_word:{word}"))
    await bot.send_message(chat_id, text, reply_markup=keyboard)

# Обработчик callback для добавления слова в словарь
async def process_add_word(callback_query: types.CallbackQuery, bot: Bot):
    word = callback_query.data.split(":")[1]
    chat_id = callback_query.from_user.id
    # Здесь можно добавить вызов CRUD-функции для сохранения слова (с деталями, если есть)
    crud.add_word_to_dictionary(chat_id, {"word": word})
    await bot.send_message(chat_id, f"Слово '{word}' добавлено в ваш словарь!")
    await callback_query.answer()

def register_words_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(lambda c: c.data.startswith("add_word:"), lambda c: process_add_word(c, bot))
    # Можно добавить команду или обработчик главного меню для слова дня, например:
    dp.register_callback_query_handler(lambda c: c.data == "menu:get_word", lambda c: send_word_of_day(c.from_user.id, bot))
