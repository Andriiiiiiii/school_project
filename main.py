import asyncio
import logging
import random
import sqlite3
import os
import tempfile

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from gtts import gTTS

# Вставьте сюда токен вашего бота
BOT_TOKEN = '7826920570:AAFNCinJxjrYMt_a_MWhYVNyYPRQKu0ELzg'

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Глобальный словарь для хранения данных по викторине (на один вопрос на пользователя)
quiz_data = {}  # ключ: chat_id, значение: dict с данными вопроса

# Список доступных тем
TOPICS = ['business', 'IT', 'travel', 'movies']

# Встроенный словарь слов для каждой темы
words_data = {
    'business': [
        {
            'word': 'profit',
            'translation': 'прибыль',
            'transcription': '/ˈprɒfɪt/',
            'example': 'The company made a huge profit last year.'
        },
        {
            'word': 'investment',
            'translation': 'инвестиция',
            'transcription': '/ɪnˈvɛstmənt/',
            'example': 'They are planning a new investment in technology.'
        },
        {
            'word': 'market',
            'translation': 'рынок',
            'transcription': '/ˈmɑːrkɪt/',
            'example': 'The market is very competitive nowadays.'
        },
        {
            'word': 'revenue',
            'translation': 'доход',
            'transcription': '/ˈrɛvənjuː/',
            'example': 'The revenue increased by 20% this quarter.'
        }
    ],
    'IT': [
        {
            'word': 'algorithm',
            'translation': 'алгоритм',
            'transcription': '/ˈælɡərɪðəm/',
            'example': 'This algorithm improves search efficiency.'
        },
        {
            'word': 'database',
            'translation': 'база данных',
            'transcription': '/ˈdeɪtəbeɪs/',
            'example': 'The database stores user information securely.'
        },
        {
            'word': 'software',
            'translation': 'программное обеспечение',
            'transcription': '/ˈsɒftwɛər/',
            'example': 'The new software update includes many features.'
        },
        {
            'word': 'cybersecurity',
            'translation': 'кибербезопасность',
            'transcription': '/ˌsaɪbərsɪˈkjʊərɪti/',
            'example': 'Cybersecurity is a top priority for companies.'
        }
    ],
    'travel': [
        {
            'word': 'journey',
            'translation': 'путешествие',
            'transcription': '/ˈdʒɜːni/',
            'example': 'Her journey across the country was unforgettable.'
        },
        {
            'word': 'itinerary',
            'translation': 'маршрут',
            'transcription': '/aɪˈtɪnərəri/',
            'example': 'The itinerary includes visits to several historic sites.'
        },
        {
            'word': 'expedition',
            'translation': 'экспедиция',
            'transcription': '/ˌɛkspəˈdɪʃən/',
            'example': 'They joined an expedition to the Arctic.'
        },
        {
            'word': 'destination',
            'translation': 'пункт назначения',
            'transcription': '/ˌdɛstɪˈneɪʃən/',
            'example': 'Paris is a popular destination for tourists.'
        }
    ],
    'movies': [
        {
            'word': 'director',
            'translation': 'режиссер',
            'transcription': '/dəˈrɛktər/',
            'example': 'The director won several awards for his film.'
        },
        {
            'word': 'screenplay',
            'translation': 'сценарий',
            'transcription': '/ˈskriːnpleɪ/',
            'example': 'The screenplay was adapted from a bestselling novel.'
        },
        {
            'word': 'actor',
            'translation': 'актер',
            'transcription': '/ˈæktər/',
            'example': 'The actor delivered a stunning performance.'
        },
        {
            'word': 'blockbuster',
            'translation': 'блокбастер',
            'transcription': '/ˈblɒkbʌstər/',
            'example': 'The movie turned out to be a blockbuster hit.'
        }
    ]
}

# Инициализация подключения к SQLite
conn = sqlite3.connect('bot.db', check_same_thread=False)
cursor = conn.cursor()

def init_db():
    """Создает необходимые таблицы в базе данных, если они отсутствуют."""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            topic TEXT DEFAULT 'business',
            word_index INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dictionary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            word TEXT,
            translation TEXT,
            transcription TEXT,
            example TEXT
        )
    ''')
    conn.commit()

init_db()  # Инициализируем базу данных

# Функции работы с базой пользователей
def add_user(chat_id: int):
    """Добавляет нового пользователя в базу, если его там ещё нет."""
    cursor.execute("SELECT chat_id FROM users WHERE chat_id = ?", (chat_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (chat_id, topic, word_index) VALUES (?, ?, ?)", (chat_id, 'business', 0))
        conn.commit()

def get_user(chat_id: int):
    """Возвращает данные пользователя (chat_id, topic, word_index)."""
    cursor.execute("SELECT chat_id, topic, word_index FROM users WHERE chat_id = ?", (chat_id,))
    return cursor.fetchone()

def update_user_topic(chat_id: int, topic: str):
    """Обновляет выбранную тему пользователя и сбрасывает счетчик слов."""
    cursor.execute("UPDATE users SET topic = ?, word_index = ? WHERE chat_id = ?", (topic, 0, chat_id))
    conn.commit()

def update_user_word_index(chat_id: int, new_index: int):
    """Обновляет индекс текущего слова для пользователя."""
    cursor.execute("UPDATE users SET word_index = ? WHERE chat_id = ?", (new_index, chat_id))
    conn.commit()

def add_word_to_dictionary(chat_id: int, word_data: dict):
    """Добавляет слово в личный словарь пользователя."""
    cursor.execute("""
        INSERT INTO dictionary (chat_id, word, translation, transcription, example)
        VALUES (?, ?, ?, ?, ?)
    """, (chat_id, word_data['word'], word_data['translation'], word_data['transcription'], word_data['example']))
    conn.commit()

def get_user_dictionary(chat_id: int):
    """Возвращает список слов из личного словаря пользователя."""
    cursor.execute("SELECT word, translation, transcription, example FROM dictionary WHERE chat_id = ?", (chat_id,))
    return cursor.fetchall()

# ------------- Обработчики команд -------------

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    """Обработчик команды /start – регистрирует пользователя и выводит приветственное сообщение."""
    chat_id = message.chat.id
    add_user(chat_id)
    await message.answer(
        "Добро пожаловать в English Learning Bot!\n\n"
        "Каждый день вы будете получать новое слово с переводом, транскрипцией и примером использования.\n"
        "Используйте команду /settings для выбора темы, /dictionary для просмотра сохранённых слов и /quiz для викторины."
    )

@dp.message_handler(commands=['settings'])
async def cmd_settings(message: types.Message):
    """Обработчик команды /settings – позволяет выбрать тему слов."""
    keyboard = InlineKeyboardMarkup(row_width=2)
    for topic in TOPICS:
        # Отображаем тему с заглавной буквы
        button = InlineKeyboardButton(text=topic.capitalize(), callback_data=f"topic:{topic}")
        keyboard.insert(button)
    await message.answer("Выберите тему для изучения:", reply_markup=keyboard)

@dp.message_handler(commands=['dictionary'])
async def cmd_dictionary(message: types.Message):
    """Обработчик команды /dictionary – выводит список слов, добавленных в личный словарь."""
    chat_id = message.chat.id
    words = get_user_dictionary(chat_id)
    if not words:
        await message.answer("Ваш словарь пуст. Добавьте слово, нажав кнопку 'Добавить в словарь'.")
    else:
        text = "Ваш личный словарь:\n\n"
        for word, translation, transcription, example in words:
            text += f"Слово: {word}\nПеревод: {translation}\nТранскрипция: {transcription}\nПример: {example}\n\n"
        await message.answer(text)

@dp.message_handler(commands=['quiz'])
async def cmd_quiz(message: types.Message):
    """Обработчик команды /quiz – запускает викторину."""
    chat_id = message.chat.id
    question = generate_quiz_question(chat_id)
    if question is None:
        await message.answer("Недостаточно выученных слов для викторины. Попробуйте позже!")
    else:
        question_text, keyboard = question
        await message.answer(question_text, reply_markup=keyboard)

# ------------- Callback Query Handlers -------------

@dp.callback_query_handler(lambda c: c.data.startswith("topic:"))
async def process_topic_selection(callback_query: types.CallbackQuery):
    """Обработка выбора темы."""
    topic = callback_query.data.split("topic:")[1]
    chat_id = callback_query.from_user.id
    update_user_topic(chat_id, topic)
    await bot.answer_callback_query(callback_query.id, f"Вы выбрали тему: {topic.capitalize()}")
    await bot.send_message(chat_id, f"Тема успешно изменена на {topic.capitalize()}.\nНачинаем обучение!")

@dp.callback_query_handler(lambda c: c.data.startswith("pronounce:"))
async def process_pronounce(callback_query: types.CallbackQuery):
    """Обработка нажатия кнопки 'Послушать произношение'."""
    # Извлекаем слово из callback_data
    word = callback_query.data.split("pronounce:")[1]
    chat_id = callback_query.from_user.id

    # Генерируем аудио с помощью gTTS
    try:
        tts = gTTS(text=word, lang='en')
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tf:
            temp_filename = tf.name
            tts.save(temp_filename)
        # Отправляем аудиофайл пользователю
        with open(temp_filename, 'rb') as audio:
            await bot.send_audio(chat_id, audio, caption=f"Произношение: {word}")
    except Exception as e:
        logger.exception("Ошибка при генерации произношения")
        await bot.send_message(chat_id, "Не удалось сгенерировать произношение.")
    finally:
        # Удаляем временный файл
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
    await bot.answer_callback_query(callback_query.id)

@dp.callback_query_handler(lambda c: c.data.startswith("add:"))
async def process_add_word(callback_query: types.CallbackQuery):
    """Обработка нажатия кнопки 'Добавить в словарь'."""
    # Извлекаем слово из callback_data
    word = callback_query.data.split("add:")[1]
    chat_id = callback_query.from_user.id

    # Получаем данные пользователя для определения выбранной темы
    user = get_user(chat_id)
    if user is None:
        await bot.answer_callback_query(callback_query.id, "Пользователь не найден.")
        return
    topic = user[1]

    # Находим данные слова в словаре по теме (если слово не найдено – ищем во всех темах)
    word_data = next((w for w in words_data.get(topic, []) if w['word'] == word), None)
    if word_data is None:
        # Поиск по всем темам
        for t in TOPICS:
            word_data = next((w for w in words_data.get(t, []) if w['word'] == word), None)
            if word_data:
                break

    if word_data:
        add_word_to_dictionary(chat_id, word_data)
        await bot.answer_callback_query(callback_query.id, "Слово добавлено в словарь!")
    else:
        await bot.answer_callback_query(callback_query.id, "Не удалось найти слово в базе.")

@dp.callback_query_handler(lambda c: c.data.startswith("start_quiz"))
async def process_start_quiz(callback_query: types.CallbackQuery):
    """Обработка нажатия кнопки 'Начать викторину' (при автоматическом предложении викторины)."""
    chat_id = callback_query.from_user.id
    question = generate_quiz_question(chat_id)
    if question is None:
        await bot.send_message(chat_id, "Недостаточно выученных слов для викторины.")
    else:
        question_text, keyboard = question
        await bot.send_message(chat_id, question_text, reply_markup=keyboard)
    await bot.answer_callback_query(callback_query.id)

@dp.callback_query_handler(lambda c: c.data.startswith("quiz:"))
async def process_quiz_answer(callback_query: types.CallbackQuery):
    """Обработка ответа на викторину."""
    chat_id = callback_query.from_user.id
    data = callback_query.data.split(":")[1]  # ожидаем "1" для правильного и "0" для неправильного ответа
    if chat_id not in quiz_data:
        await bot.answer_callback_query(callback_query.id, "Вопрос устарел, попробуйте еще раз!")
        return

    correct_translation = quiz_data[chat_id]['correct']
    word = quiz_data[chat_id]['word']
    if data == "1":
        reply_text = "Правильно! 🎉"
    else:
        reply_text = f"Неправильно. Правильный ответ: {correct_translation}"
    # Удаляем данные вопроса
    del quiz_data[chat_id]
    # Редактируем сообщение с викториной, добавляя результат
    try:
        await bot.edit_message_text(reply_text, chat_id=chat_id, message_id=callback_query.message.message_id)
    except Exception as e:
        logger.exception("Ошибка при редактировании сообщения викторины")
    await bot.answer_callback_query(callback_query.id)

# ------------- Функции для генерации викторины -------------

def generate_quiz_question(chat_id: int):
    """
    Генерирует вопрос викторины для пользователя.
    Выбираем слово из уже пройденных (если есть) или из всего списка по теме.
    Возвращает кортеж (текст вопроса, клавиатура с вариантами ответов).
    """
    user = get_user(chat_id)
    if user is None:
        return None
    topic = user[1]
    word_index = user[2]
    word_list = words_data.get(topic, [])

    if not word_list:
        return None

    # Если пользователь уже получил несколько слов – выбираем из уже пройденных
    if word_index > 0:
        candidate_pool = word_list[:word_index]
    else:
        candidate_pool = word_list

    if not candidate_pool:
        candidate_pool = word_list

    correct_word = random.choice(candidate_pool)
    correct_translation = correct_word['translation']

    # Формируем варианты ответа: 1 правильный и 3 случайных других (если возможно)
    options = [correct_translation]
    distractors = [w['translation'] for w in candidate_pool if w['translation'] != correct_translation]

    # Если недостаточно вариантов в пройденных словах – берем из полного списка
    if len(distractors) < 3:
        distractors += [w['translation'] for w in word_list if w['translation'] not in options + distractors]

    distractors = list(set(distractors))
    random.shuffle(distractors)
    options += distractors[:3]
    random.shuffle(options)

    # Формируем inline-клавиатуру с вариантами ответа
    keyboard = InlineKeyboardMarkup(row_width=2)
    for opt in options:
        # callback_data = "quiz:1" для правильного ответа, иначе "quiz:0"
        correct_flag = "1" if opt == correct_translation else "0"
        button = InlineKeyboardButton(text=opt, callback_data=f"quiz:{correct_flag}")
        keyboard.insert(button)

    # Сохраняем данные викторины для данного пользователя (чтобы при неправильном ответе можно было показать правильный)
    quiz_data[chat_id] = {
        'word': correct_word['word'],
        'correct': correct_translation
    }

    # Текст вопроса (пример: "Как переводится слово 'software'?")
    question_text = (
        f"Как переводится слово «{correct_word['word']}»?\n"
        f"Транскрипция: {correct_word['transcription']}\n"
        f"Пример использования: {correct_word['example']}"
    )
    return question_text, keyboard

# ------------- Функции планировщика -------------

async def send_daily_words():
    """Рассылка нового слова каждому пользователю (ежедневно)."""
    cursor.execute("SELECT chat_id, topic, word_index FROM users")
    users = cursor.fetchall()
    for chat_id, topic, word_index in users:
        word_list = words_data.get(topic, [])
        if not word_list:
            continue

        # Если индекс вышел за пределы списка, начинаем с начала
        if word_index >= len(word_list):
            word_index = 0

        word_item = word_list[word_index]

        # Формируем сообщение
        text = (
            f"Новое слово дня:\n\n"
            f"Слово: {word_item['word']}\n"
            f"Перевод: {word_item['translation']}\n"
            f"Транскрипция: {word_item['transcription']}\n"
            f"Пример: {word_item['example']}"
        )
        # Формируем клавиатуру с двумя кнопками: для произношения и для добавления в словарь
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("Послушать произношение", callback_data=f"pronounce:{word_item['word']}"),
            InlineKeyboardButton("Добавить в словарь", callback_data=f"add:{word_item['word']}")
        )
        try:
            await bot.send_message(chat_id, text, reply_markup=keyboard)
        except Exception as e:
            logger.exception(f"Ошибка отправки сообщения пользователю {chat_id}: {e}")

        # Обновляем индекс для пользователя
        update_user_word_index(chat_id, word_index + 1)

async def send_quiz_prompt():
    """Раз в 3 дня отправляет пользователю приглашение пройти викторину."""
    cursor.execute("SELECT chat_id FROM users")
    users = cursor.fetchall()
    for (chat_id,) in users:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("Начать викторину", callback_data="start_quiz"))
        try:
            await bot.send_message(chat_id, "Пора пройти викторину по пройденным словам! Нажмите кнопку ниже для начала.", reply_markup=keyboard)
        except Exception as e:
            logger.exception(f"Ошибка отправки викторины пользователю {chat_id}: {e}")

# ------------- Настройка планировщика -------------

scheduler = AsyncIOScheduler()

# Запланировать ежедневную рассылку в 9:00 утра (укажите нужное время по вашему часовому поясу)
scheduler.add_job(send_daily_words, 'cron', hour=9, minute=0)

# Запланировать викторину раз в 3 дня (начнётся с момента запуска бота)
scheduler.add_job(send_quiz_prompt, 'interval', days=3)

# ------------- Точка входа -------------

async def on_startup(dispatcher: Dispatcher):
    """Функция, вызываемая при запуске бота."""
    scheduler.start()
    logger.info("Планировщик запущен.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
