# handlers/commands.py
from __future__ import annotations

import logging
from functools import partial

from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand, MenuButtonCommands

from config import DEFAULT_SETS
from database import crud
from keyboards.main_menu import main_menu_keyboard
from keyboards.reply_keyboards import get_main_menu_keyboard
from utils.helpers import get_daily_words_for_user
from utils.visual_helpers import format_daily_words_message

logger = logging.getLogger(__name__)

# ─────────────────────────── КОМАНДЫ БОТА (список) ─────────────────────────
BOT_COMMANDS: list[BotCommand] = [
    BotCommand("start", "Начать заново"),
    BotCommand("menu", "Главное меню"),
    BotCommand("words", "Слова дня"),
    BotCommand("quiz", "Тест дня"),
    BotCommand("dictionary", "Мой словарь"),
    BotCommand("settings", "Персонализация"),
    BotCommand("help", "Справка"),
]


async def set_commands(bot: Bot) -> None:
    """Регистрация /команд в клиентском меню."""
    await bot.set_my_commands(BOT_COMMANDS)
    
    # Явно устанавливаем кнопку меню для всех чатов
    try:
        # Глобальная установка кнопки меню команд
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        logger.info("Кнопка меню команд установлена глобально")
    except Exception as e:
        logger.error(f"Ошибка при установке кнопки меню: {e}")


# ─────────────────────────────── /START ────────────────────────────────────
async def cmd_start(message: types.Message, bot: Bot) -> None:
    chat_id = message.chat.id
    logger.info("Команда /start от chat_id=%s", chat_id)

    try:
        # Явно устанавливаем кнопку меню команд для этого конкретного чата
        await bot.set_chat_menu_button(chat_id=chat_id, menu_button=MenuButtonCommands())
        
        # ─── регистрация нового пользователя ───────────────────────────────
        if not crud.get_user(chat_id):
            crud.add_user(chat_id)
            logger.info("Создан новый пользователь %s", chat_id)

            default_set = DEFAULT_SETS.get("A1")
            if default_set:
                crud.update_user_chosen_set(chat_id, default_set)
                from handlers.settings import user_set_selection

                user_set_selection[chat_id] = default_set
                logger.info("Базовый сет %s назначен пользователю %s", default_set, chat_id)

            # Начинаем процесс онбординга для нового пользователя
            from handlers.onboarding import start_onboarding
            await start_onboarding(message, bot)
            return

        # ─── приветственное сообщение + главное меню ───────────────────────
        await message.answer(
            "👋 *Добро пожаловать в English Learning Bot!*\n\n"
            "• Ежедневные наборы слов\n"
            "• Квизы для закрепления\n"
            "• Персональный словарь\n"
            "• Тестирование уровня\n\n"
            "Выберите действие:",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )

    except Exception as exc:  # fallback
        logger.exception("Ошибка в cmd_start: %s", exc)
        await message.answer(
            "👋 *Добро пожаловать!*\n\nВыберите действие:",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )

# ──────────────────────── НОВЫЕ ОБРАБОТЧИКИ КОМАНД ────────────────────────────────
async def cmd_words(message: types.Message, bot: Bot) -> None:
    """Показывает слова дня."""
    chat_id = message.chat.id
    user = crud.get_user(chat_id)
    
    if not user:
        await message.answer("⚠️ Профиль не найден. Используйте /start.", parse_mode="Markdown")
        return

    # Получаем слова дня напрямую, без использования callback
    from config import REMINDER_START, DURATION_HOURS
    from utils.helpers import get_user_settings
    
    words, reps = get_user_settings(chat_id)
    result = get_daily_words_for_user(
        chat_id, user[1], words, reps,
        first_time=REMINDER_START, duration_hours=DURATION_HOURS
    )
    
    if result is None:
        await message.answer(f"⚠️ Нет слов для уровня {user[1]}.", parse_mode="Markdown")
        return
    elif len(result) == 3 and result[:2] == (None, None):
        # Требуется подтверждение смены сета
        default_set = result[2]
        current_set = user[6] or "не выбран"
        from keyboards.submenus import set_change_confirm_keyboard
        
        text = (
            "⚠️ *Внимание! Смена сета сбросит прогресс.*\n\n"
            f"Текущий сет: *{current_set}*\n"
            f"Текущий уровень: *{user[1]}*\n\n"
            f"Сет не соответствует уровню.\n"
            f"Сменить на базовый *{default_set}*?\n"
        )
        await message.answer(text, parse_mode="Markdown", 
                            reply_markup=set_change_confirm_keyboard(default_set))
        return
    
    messages, times = result
    await message.answer(
        format_daily_words_message(messages, times),
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )

async def cmd_quiz(message: types.Message, bot: Bot) -> None:
    """Запускает квиз со словами дня."""
    chat_id = message.chat.id
    user = crud.get_user(chat_id)
    
    if not user:
        await message.answer("⚠️ Профиль не найден. Используйте /start.", parse_mode="Markdown")
        return
    
    # Инициализируем квиз напрямую
    from config import DURATION_HOURS, REMINDER_START
    from handlers.quiz import quiz_states, poll_to_user, poll_to_index, nav_messages
    from utils.helpers import daily_words_cache, get_daily_words_for_user
    from utils.quiz_helpers import load_quiz_data
    from utils.quiz_utils import generate_quiz_options
    from utils.visual_helpers import extract_english
    
    level = user[1]
    # Опциональный сет из настроек
    try:
        from handlers.settings import user_set_selection
        chosen_set = user_set_selection.get(chat_id)
    except ImportError:
        chosen_set = None

    learned = {extract_english(w[0]).lower() for w in crud.get_learned_words(chat_id)}

    # Получаем слова дня
    get_daily_words_for_user(
        chat_id, level, user[2], user[3],
        first_time=REMINDER_START, duration_hours=DURATION_HOURS,
        chosen_set=chosen_set,
    )
    entry = daily_words_cache.get(chat_id)
    if not entry:
        await message.answer("⚠️ Нет слов для квиза.")
        return

    # Используем уникальные слова из кэша
    if len(entry) > 8 and entry[8]:
        unique_words = entry[8]
    else:
        raw = [m.replace("🔹 ", "").strip() for m in entry[1]]
        if raw and raw[0].startswith(("🎓", "⚠️")):
            raw.pop(0)
        unique_words = raw

    revision = bool(len(entry) > 9 and entry[9])
    source = unique_words if revision else [w for w in unique_words if extract_english(w).lower() not in learned]
    
    if not source:
        await message.answer("Все слова уже выучены! Попробуйте завтра.")
        return

    # Подготовка вопросов для квиза
    quiz_data = load_quiz_data(level, chosen_set)
    if not quiz_data:
        await message.answer("⚠️ Не удалось создать вопросы.")
        return
        
    mapping = {item["word"].lower(): item["translation"] for item in quiz_data}
    all_trans = [item["translation"] for item in quiz_data]
    questions = []
    
    for src in source:
        key = extract_english(src).lower()
        correct = mapping.get(key) or mapping.get(src.lower())
        if not correct:
            continue
        opts, idx = generate_quiz_options(correct, all_trans, 4)
        questions.append({
            "word": src,
            "correct": correct,
            "options": opts,
            "correct_index": idx,
            "is_revision": revision,
        })
    
    if not questions:
        await message.answer("⚠️ Не удалось создать вопросы.")
        return

    # Инициализируем состояние квиза
    quiz_states[chat_id] = {
        "questions": questions,
        "current": 0,
        "correct": 0,
        "revision": revision,
        "answered": set(),
    }
    
    # Отправляем первый вопрос
    from handlers.quiz import _send_question
    await _send_question(chat_id, bot)
    
    await message.answer("Квиз запущен! Отвечайте на вопросы в опросах выше.")

async def cmd_dictionary(message: types.Message, bot: Bot) -> None:
    """Показывает словарь пользователя."""
    chat_id = message.chat.id
    
    # Получаем выученные слова напрямую
    learned = crud.get_learned_words(chat_id)
    
    from utils.visual_helpers import format_dictionary_message
    from keyboards.submenus import dictionary_menu_keyboard
    
    if not learned:
        text = (
            "📚 *Ваш словарь пуст*\n\n"
            "Пройдите квизы, чтобы добавить слова в свой словарь!"
        )
    else:
        text = format_dictionary_message(learned)

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=dictionary_menu_keyboard()
    )

async def cmd_settings(message: types.Message, bot: Bot) -> None:
    """Показывает меню настроек."""
    from keyboards.submenus import settings_menu_keyboard
    
    await message.answer(
        "Настройки бота:", 
        reply_markup=settings_menu_keyboard()
    )

async def cmd_menu(message: types.Message) -> None:
    await message.answer("📋 Главное меню:", reply_markup=main_menu_keyboard())

async def cmd_help(message: types.Message) -> None:
    from keyboards.submenus import help_menu_keyboard

    await message.answer(
        "*Справка по боту*\n\n"
        "English Learning Bot помогает изучать английский язык через:\n"
        "• Ежедневные подборки слов\n"
        "• Квизы и тесты\n"
        "• Персональный словарь\n\n"
        "Выберите раздел справки:",
        parse_mode="Markdown",
        reply_markup=help_menu_keyboard(),
    )

# ───────────────────────── РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ──────────────────────────
def register_command_handlers(dp: Dispatcher, bot: Bot) -> None:
    """Подключает все вышеописанные команды к диспетчеру."""
    dp.register_message_handler(partial(cmd_start, bot=bot), commands="start", state="*")
    dp.register_message_handler(cmd_menu, commands="menu")
    dp.register_message_handler(partial(cmd_words, bot=bot), commands="words")
    dp.register_message_handler(partial(cmd_quiz, bot=bot), commands="quiz")
    dp.register_message_handler(partial(cmd_dictionary, bot=bot), commands="dictionary")
    dp.register_message_handler(partial(cmd_settings, bot=bot), commands="settings")
    dp.register_message_handler(cmd_help, commands="help")

    # текстовая фраза «Перезапуск /start» (если используется в интерфейсе)
    dp.register_message_handler(
        partial(cmd_start, bot=bot),
        lambda m: m.text and "Перезапуск /start" in m.text,
    )