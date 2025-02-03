# handlers.py
import asyncio
import random
import os
import tempfile
import logging
from datetime import datetime

from aiogram import types, Dispatcher, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from gtts import gTTS

import database

# Глобальный словарь для хранения данных по викторине (старый функционал)
quiz_data = {}

# Глобальный словарь для хранения состояния теста уровня
test_states = {}  # ключ: chat_id, значение: dict с полями: current_level, words, index, batch_size

# Определяем порядок уровней
levels_order = ["A1", "A2", "B1", "B2", "C1", "C2"]

# Функция формирования главного меню
def main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📖 Получить слово дня", callback_data="menu:get_word"),
        InlineKeyboardButton("🔧 Настройки", callback_data="menu:settings"),
        InlineKeyboardButton("📚 Мой словарь", callback_data="menu:my_dictionary"),
        InlineKeyboardButton("📝 Викторина", callback_data="menu:quiz"),
        InlineKeyboardButton("❓ Помощь", callback_data="menu:help"),
        InlineKeyboardButton("📝 Тест уровня", callback_data="menu:test")
    )
    return keyboard

def register_handlers(dp: Dispatcher, bot: Bot):
    """Регистрирует все обработчики команд и callback-запросов."""
    # --- Команда /start ---
    @dp.message_handler(commands=['start'])
    async def cmd_start(message: types.Message):
        chat_id = message.chat.id
        database.add_user(chat_id)
        await message.answer(
            "Добро пожаловать в English Learning Bot!\n\n"
            "Выберите действие из меню ниже:",
            reply_markup=main_menu_keyboard()
        )

    # --- Команда /help ---
    @dp.message_handler(commands=['help'])
    async def cmd_help(message: types.Message):
        help_text = (
            "Список команд:\n"
            "/start - Перезапустить бота\n"
            "/help - Помощь\n"
            "/settings - Настройки\n"
            "/dictionary - Мой словарь\n"
            "/quiz - Викторина\n"
            "/test - Тест уровня\n\n"
            "Также используйте главное меню для навигации."
        )
        await message.answer(help_text, reply_markup=main_menu_keyboard())

    # --- Команда /test (для прохождения теста уровня) ---
    @dp.message_handler(commands=['test'])
    async def cmd_test(message: types.Message):
        chat_id = message.chat.id
        await start_test(chat_id, bot)

    # --- Главное меню (обработка inline-кнопок) ---
    @dp.callback_query_handler(lambda c: c.data.startswith("menu:"))
    async def process_main_menu(callback_query: types.CallbackQuery):
        action = callback_query.data.split(":")[1]
        chat_id = callback_query.from_user.id

        if action == "get_word":
            await send_proficiency_word_of_day(chat_id, bot)
        elif action == "settings":
            await send_settings_menu(chat_id, bot)
        elif action == "my_dictionary":
            await send_dictionary(chat_id, bot)
        elif action == "quiz":
            await send_quiz(chat_id, bot)
        elif action == "help":
            await send_help(chat_id, bot)
        elif action == "test":
            await start_test(chat_id, bot)
        await callback_query.answer()

    # --- Остальные обработчики (старый функционал) ---
    @dp.callback_query_handler(lambda c: c.data.startswith("topic:"))
    async def process_topic_selection(callback_query: types.CallbackQuery):
        topic = callback_query.data.split(":")[1]
        chat_id = callback_query.from_user.id
        database.update_user_topic(chat_id, topic)
        await bot.send_message(chat_id, f"Тема успешно изменена на {topic.capitalize()}.", reply_markup=main_menu_keyboard())
        await callback_query.answer()

    @dp.callback_query_handler(lambda c: c.data == "settime")
    async def process_set_time(callback_query: types.CallbackQuery):
        chat_id = callback_query.from_user.id
        await bot.send_message(chat_id, "Введите время для получения слова дня в формате HH:MM (например, 09:00):")
        await callback_query.answer()

    @dp.message_handler(lambda message: message.text and len(message.text) == 5 and message.text[2] == ':')
    async def process_time_input(message: types.Message):
        chat_id = message.chat.id
        time_str = message.text
        try:
            datetime.strptime(time_str, "%H:%M")
            database.update_user_reminder_time(chat_id, time_str)
            await message.answer(f"Время получения слова дня обновлено на {time_str}.", reply_markup=main_menu_keyboard())
        except ValueError:
            await message.answer("Неверный формат времени. Попробуйте снова.")

    @dp.callback_query_handler(lambda c: c.data.startswith("pronounce:"))
    async def process_pronounce(callback_query: types.CallbackQuery):
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

    @dp.callback_query_handler(lambda c: c.data.startswith("add:"))
    async def process_add_word(callback_query: types.CallbackQuery):
        word = callback_query.data.split(":")[1]
        chat_id = callback_query.from_user.id
        user = database.get_user(chat_id)
        if not user:
            await bot.send_message(chat_id, "Пользователь не найден.")
            return
        topic = user[1]
        word_data = next((w for w in database.words_data.get(topic, []) if w['word'] == word), None)
        if word_data is None:
            for t in database.TOPICS:
                word_data = next((w for w in database.words_data.get(t, []) if w['word'] == word), None)
                if word_data:
                    break
        if word_data:
            database.add_word_to_dictionary(chat_id, word_data)
            await bot.send_message(chat_id, "Слово добавлено в словарь!", reply_markup=main_menu_keyboard())
        else:
            await bot.send_message(chat_id, "Не удалось найти слово в базе.", reply_markup=main_menu_keyboard())
        await callback_query.answer()

    @dp.callback_query_handler(lambda c: c.data.startswith("example:"))
    async def process_example(callback_query: types.CallbackQuery):
        word = callback_query.data.split(":")[1]
        chat_id = callback_query.from_user.id
        user = database.get_user(chat_id)
        topic = user[1] if user else 'business'
        word_data = next((w for w in database.words_data.get(topic, []) if w['word'] == word), None)
        if word_data:
            await bot.send_message(chat_id, f"Пример использования:\n{word_data['example']}", reply_markup=main_menu_keyboard())
        else:
            await bot.send_message(chat_id, "Пример не найден.", reply_markup=main_menu_keyboard())
        await callback_query.answer()

    @dp.callback_query_handler(lambda c: c.data.startswith("quiz:"))
    async def process_quiz_answer(callback_query: types.CallbackQuery):
        chat_id = callback_query.from_user.id
        data = callback_query.data.split(":")[1]
        if chat_id not in quiz_data:
            await bot.send_message(chat_id, "Вопрос устарел, попробуйте еще раз.", reply_markup=main_menu_keyboard())
            return
        correct_translation = quiz_data[chat_id]['correct']
        reply_text = "Правильно! 🎉" if data == "1" else f"Неправильно. Правильный ответ: {correct_translation}"
        del quiz_data[chat_id]
        try:
            await bot.edit_message_text(reply_text, chat_id=chat_id, message_id=callback_query.message.message_id)
        except Exception as e:
            logging.exception("Ошибка редактирования сообщения викторины")
        await callback_query.answer()

    @dp.message_handler(commands=['quiz'])
    async def cmd_quiz(message: types.Message):
        await send_quiz(message.chat.id, bot)

    @dp.message_handler(commands=['dictionary'])
    async def cmd_dictionary(message: types.Message):
        await send_dictionary(message.chat.id, bot)

    # --- Обработчики для теста уровня ---
    @dp.callback_query_handler(lambda c: c.data.startswith("test:"))
    async def process_test_answer(callback_query: types.CallbackQuery):
        chat_id = callback_query.from_user.id
        answer = callback_query.data.split(":")[1]  # 'know' или 'donot'
        if chat_id not in test_states:
            await bot.send_message(chat_id, "Тест не запущен. Используйте команду /test для начала.", reply_markup=main_menu_keyboard())
            await callback_query.answer()
            return
        state = test_states[chat_id]
        current_level = state['current_level']
        if answer == "donot":
            # Если слово не известно – завершаем тест и сохраняем текущий уровень как итог
            database.update_user_proficiency(chat_id, current_level)
            await bot.send_message(chat_id, f"Тест завершён. Ваш уровень: {current_level}", reply_markup=main_menu_keyboard())
            del test_states[chat_id]
            await callback_query.answer()
            return
        else:  # answer == "know"
            state['index'] += 1
            if state['index'] >= state['batch_size']:
                # Если все слова пакета отвечены правильно – повышаем уровень (если он не последний)
                current_index = levels_order.index(current_level)
                if current_index < len(levels_order) - 1:
                    new_level = levels_order[current_index + 1]
                    state['current_level'] = new_level
                    await bot.send_message(chat_id, f"Поздравляем! Вы прошли уровень {current_level}. Переход на уровень {new_level}.", reply_markup=main_menu_keyboard())
                    words = load_words_for_level(new_level)
                    state['words'] = words
                    state['index'] = 0
                else:
                    database.update_user_proficiency(chat_id, current_level)
                    await bot.send_message(chat_id, f"Тест завершён. Ваш уровень: {current_level}", reply_markup=main_menu_keyboard())
                    del test_states[chat_id]
                    await callback_query.answer()
                    return
            await send_test_question(chat_id, bot)
            await callback_query.answer()

# Функция загрузки слов из файла для теста уровня
def load_words_for_level(level: str):
    filename = f"{level}.txt"
    if not os.path.exists(filename):
        return []
    with open(filename, encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]
    # Если слов больше 5 – выбираем случайные 5, иначе берём все
    if len(words) > 5:
        return random.sample(words, 5)
    return words

# Функция начала теста уровня
async def start_test(chat_id: int, bot: Bot):
    initial_level = "A1"
    words = load_words_for_level(initial_level)
    if not words:
        await bot.send_message(chat_id, f"Файл {initial_level}.txt не найден или пуст.", reply_markup=main_menu_keyboard())
        return
    test_states[chat_id] = {
        'current_level': initial_level,
        'words': words,
        'index': 0,
        'batch_size': 5
    }
    await bot.send_message(chat_id, f"Начинаем тест уровня. Уровень: {initial_level}")
    await send_test_question(chat_id, bot)

# Функция отправки вопроса теста уровня
async def send_test_question(chat_id: int, bot: Bot):
    state = test_states.get(chat_id)
    if not state:
        return
    if state['index'] >= len(state['words']):
        await bot.send_message(chat_id, "Вопросы закончились. Тест завершён.", reply_markup=main_menu_keyboard())
        del test_states[chat_id]
        return
    word = state['words'][state['index']]
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Знаю", callback_data="test:know"),
        InlineKeyboardButton("Не знаю", callback_data="test:donot")
    )
    await bot.send_message(chat_id, f"Знаете ли вы слово: {word}?", reply_markup=keyboard)

# Функция отправки слова дня с учётом уровня владения
async def send_proficiency_word_of_day(chat_id: int, bot: Bot):
    proficiency = database.get_user_proficiency(chat_id)
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
        await bot.send_message(chat_id, f"Файл {next_level}.txt не найден или пуст.", reply_markup=main_menu_keyboard())
        return
    word = random.choice(words)
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔊 Послушать", callback_data=f"pronounce:{word}"),
        InlineKeyboardButton("📚 Добавить в словарь", callback_data=f"add:{word}")
    )
    await bot.send_message(chat_id, f"Слово дня (уровень {next_level}): {word}", reply_markup=keyboard)

# Функция отправки меню настроек
async def send_settings_menu(chat_id: int, bot: Bot):
    keyboard = InlineKeyboardMarkup(row_width=2)
    topic_buttons = [InlineKeyboardButton(text=t.capitalize(), callback_data=f"topic:{t}") for t in database.TOPICS]
    keyboard.add(*topic_buttons)
    keyboard.add(InlineKeyboardButton("Установить время рассылки", callback_data="settime"))
    keyboard.add(InlineKeyboardButton("Назад", callback_data="menu:help"))
    await bot.send_message(chat_id, "Настройки:", reply_markup=keyboard)

# Функция отправки личного словаря
async def send_dictionary(chat_id: int, bot: Bot):
    words = database.get_user_dictionary(chat_id)
    if not words:
        await bot.send_message(chat_id, "Ваш словарь пуст.", reply_markup=main_menu_keyboard())
    else:
        text = "Ваш личный словарь:\n\n"
        for word, translation, transcription, example in words:
            text += (f"Слово: {word}\n"
                     f"Перевод: {translation}\n"
                     f"Транскрипция: {transcription}\n"
                     f"Пример: {example}\n\n")
        await bot.send_message(chat_id, text, reply_markup=main_menu_keyboard())

# Функция отправки викторины (старый функционал)
async def send_quiz(chat_id: int, bot: Bot):
    question = generate_quiz_question(chat_id)
    if question is None:
        await bot.send_message(chat_id, "Недостаточно выученных слов для викторины. Попробуйте позже!", reply_markup=main_menu_keyboard())
    else:
        question_text, keyboard = question
        await bot.send_message(chat_id, question_text, reply_markup=keyboard)

# Функция отправки помощи и списка команд
async def send_help(chat_id: int, bot: Bot):
    help_text = (
        "Список команд:\n"
        "/start - Перезапустить бота\n"
        "/help - Помощь\n"
        "/settings - Настройки\n"
        "/dictionary - Мой словарь\n"
        "/quiz - Викторина\n"
        "/test - Тест уровня\n\n"
        "Обратная связь: @YourSupportUsername"
    )
    await bot.send_message(chat_id, help_text, reply_markup=main_menu_keyboard())

# Функция генерации вопроса викторины (старый функционал)
def generate_quiz_question(chat_id: int):
    user = database.get_user(chat_id)
    if not user:
        return None
    topic = user[1]
    word_index = user[2]
    word_list = database.words_data.get(topic, [])
    if not word_list:
        return None
    candidate_pool = word_list[:word_index] if word_index > 0 else word_list
    if not candidate_pool:
        candidate_pool = word_list
    correct_word = random.choice(candidate_pool)
    correct_translation = correct_word['translation']
    options = [correct_translation]
    distractors = [w['translation'] for w in candidate_pool if w['translation'] != correct_translation]
    if len(distractors) < 3:
        distractors += [w['translation'] for w in word_list if w['translation'] not in options + distractors]
    distractors = list(set(distractors))
    random.shuffle(distractors)
    options += distractors[:3]
    random.shuffle(options)
    keyboard = InlineKeyboardMarkup(row_width=2)
    for opt in options:
        correct_flag = "1" if opt == correct_translation else "0"
        button = InlineKeyboardButton(text=opt, callback_data=f"quiz:{correct_flag}")
        keyboard.insert(button)
    quiz_data[chat_id] = {
        'word': correct_word['word'],
        'correct': correct_translation
    }
    question_text = (
        f"Как переводится слово «{correct_word['word']}»?\n"
        f"Транскрипция: {correct_word['transcription']}\n"
        f"Пример: {correct_word['example']}"
    )
    return question_text, keyboard

# Функция для авторассылки слова дня (старый функционал)
async def check_and_send_daily_words(bot: Bot):
    now = datetime.now().strftime("%H:%M")
    cur = database.conn.cursor()
    cur.execute("SELECT chat_id, topic, word_index, reminder_time FROM users")
    users = cur.fetchall()
    for chat_id, topic, word_index, reminder_time in users:
        if now == reminder_time:
            word_list = database.words_data.get(topic, [])
            if not word_list:
                continue
            if word_index >= len(word_list):
                word_index = 0
            word_item = word_list[word_index]
            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                InlineKeyboardButton("🔊 Послушать", callback_data=f"pronounce:{word_item['word']}"),
                InlineKeyboardButton("📖 Примеры", callback_data=f"example:{word_item['word']}"),
                InlineKeyboardButton("📚 Добавить в словарь", callback_data=f"add:{word_item['word']}")
            )
            text = (
                f"Слово дня:\n\n"
                f"Слово: {word_item['word']}\n"
                f"Перевод: {word_item['translation']}\n"
                f"Транскрипция: {word_item['transcription']}\n"
                f"Пример: {word_item['example']}"
            )
            try:
                await bot.send_message(chat_id, text, reply_markup=keyboard)
                database.update_user_word_index(chat_id, word_index + 1)
            except Exception as e:
                logging.exception(f"Ошибка отправки слова пользователю {chat_id}: {e}")
