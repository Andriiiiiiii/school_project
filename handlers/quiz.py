# Полное исправление файла handlers/quiz.py

"""
Тест «Слова дня»: встроенные quiz-поллы с навигацией.
"""

import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Poll, PollAnswer

from config import DURATION_HOURS, REMINDER_START
from database import crud
from utils.helpers import daily_words_cache, get_daily_words_for_user
from utils.quiz_helpers import load_quiz_data
from utils.quiz_utils import generate_quiz_options
from utils.sticker_helper import get_congratulation_sticker, send_sticker_with_menu
from utils.visual_helpers import extract_english, format_progress_bar, format_result_message

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────
#   Глобальное состояние
# ───────────────────────────────────────────────────────────────
quiz_states: dict[int, dict] = {}
poll_to_user: dict[str, int] = {}
poll_to_index: dict[str, int] = {}
nav_messages: dict[int, int] = {}
# ───────────────────────────────────────────────────────────────


def _make_nav(prefix: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру навигации с двумя кнопками в ряд."""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🛑 Закончить тест", callback_data=f"{prefix}:back"),
        InlineKeyboardButton("⏭️ Следующее слово", callback_data=f"{prefix}:skip")
    )
    return kb


def _generate_questions(daily: list[str], level: str, chosen_set: str | None, revision: bool) -> list[dict]:
    quiz_data = load_quiz_data(level, chosen_set)
    if not quiz_data:
        logger.warning("No quiz data for level=%s set=%s", level, chosen_set)
        return []

    mapping = {item["word"].lower(): item["translation"] for item in quiz_data}
    all_trans = [item["translation"] for item in quiz_data]
    questions: list[dict] = []

    for src in daily:
        key = extract_english(src).lower()
        correct = mapping.get(key) or mapping.get(src.lower())
        if not correct:
            logger.warning("No translation for %s", src)
            continue
        opts, idx = generate_quiz_options(correct, all_trans, 4)
        questions.append({
            "word": src,
            "correct": correct,
            "options": opts,
            "correct_index": idx,
            "is_revision": revision,
        })
        logger.debug("Q: %s → %s (idx=%d)", src, correct, idx)
    return questions


async def _send_question(chat_id: int, bot: Bot) -> None:
    """Отправляет вопрос пользователю с кнопками навигации."""
    state = quiz_states.get(chat_id)
    if not state:
        return

    idx = state["current"]
    if idx >= len(state["questions"]):
        # Если вопросы закончились, завершаем тест
        await _finish_quiz(chat_id, bot)
        return

    q = state["questions"][idx]

    poll: Poll = await bot.send_poll(
        chat_id=chat_id,
        question=f"Какой перевод слова «{extract_english(q['word'])}»?",
        options=q["options"],
        type="quiz",
        correct_option_id=q["correct_index"],
        explanation=f"Вопрос {idx+1}/{len(state['questions'])}"
                    + (" | Повторение" if q["is_revision"] else ""),
        is_anonymous=False,
    )
    pid = str(poll.poll.id)
    poll_to_user[pid] = chat_id
    poll_to_index[pid] = idx

    # Отправляем сообщение с прогрессом и кнопками навигации
    total_questions = len(state["questions"])
    progress_bar = format_progress_bar(idx + 1, total_questions, 10)
    
    # Удаляем предыдущее сообщение с навигацией, если оно есть
    old_msg_id = nav_messages.pop(chat_id, None)
    if old_msg_id:
        try:
            await bot.delete_message(chat_id, old_msg_id)
        except Exception as e:
            logger.error(f"Не удалось удалить старое сообщение: {e}")
    
    # Отправляем новое сообщение с навигацией
    try:
        msg = await bot.send_message(
            chat_id,
            f"📊 Прогресс: {idx+1}/{total_questions}\n{progress_bar}",
            reply_markup=_make_nav("quiz")
        )
        nav_messages[chat_id] = msg.message_id
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения с навигацией: {e}")

async def _finish_quiz(chat_id: int, bot: Bot) -> None:
    """Завершает тест и отображает результаты."""
    state = quiz_states.pop(chat_id, None)
    if not state:
        return

    # Удаляем последнее сообщение с навигацией
    old_msg_id = nav_messages.pop(chat_id, None)
    if old_msg_id:
        try:
            await bot.delete_message(chat_id, old_msg_id)
        except Exception:
            pass

    correct, total = state["correct"], len(state["questions"])
    result = format_result_message(correct, total, state["revision"])
    
    # Увеличиваем streak при прохождении теста дня
    try:
        from database.crud import increment_user_streak, get_user_streak
        from datetime import datetime
        
        # Получаем streak до инкремента
        old_streak, _ = get_user_streak(chat_id)
        
        # Инкрементируем streak
        new_streak = increment_user_streak(chat_id)
        
        # Проверяем, увеличился ли streak (значит, это первый тест за день)
        if new_streak > old_streak:
            result += f"\n🔥 Дней подряд: {new_streak}"
            if new_streak >= 7:
                result += "\n🎯 Отличная последовательность!"
        else:
            result += f"\n🔥 Дней подряд: {new_streak} (уже проходили тест сегодня)"
                
    except Exception as e:
        logger.error(f"Ошибка обновления streak для пользователя {chat_id}: {e}")
    
    await bot.send_message(chat_id, result, parse_mode="Markdown")
    
    from keyboards.main_menu import main_menu_keyboard
    await bot.send_message(chat_id, "Тест завершён.", reply_markup=main_menu_keyboard())

async def start_quiz(cb: types.CallbackQuery, bot: Bot) -> None:
    """Начинает тест со словами дня. Исправленная версия с правильной обработкой режима повторения."""
    chat_id = cb.from_user.id
    logger.info("StartQuiz chat=%s", chat_id)

    # Удаляем старую навигацию
    old_msg_id = nav_messages.pop(chat_id, None)
    if old_msg_id:
        try:
            await bot.delete_message(chat_id, old_msg_id)
        except Exception:
            pass

    user = crud.get_user(chat_id)
    if not user:
        await bot.send_message(chat_id, "Профиль не найден. Используйте /start.")
        await cb.answer()
        return

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
        await bot.send_message(chat_id, "⚠️ Нет слов для теста.")
        await cb.answer()
        return

    # Используем уникальные слова из кэша (позиция 8)
    if len(entry) > 8 and entry[8]:
        # Используем уникальные слова из кэша
        unique_words = entry[8]
    else:
        # Если уникальные слова не доступны, извлекаем их из сообщений
        raw = [m.replace("🔹 ", "").strip() for m in entry[1]]
        if raw and raw[0].startswith(("🎓", "⚠️")):
            raw.pop(0)
        unique_words = raw

    # ИСПРАВЛЕННАЯ ЛОГИКА ОБРАБОТКИ РЕЖИМА ПОВТОРЕНИЯ
    revision = bool(len(entry) > 9 and entry[9])
    
    if revision:
        # В режиме повторения тестируем все слова, поскольку все уже выучены
        source = unique_words
    else:
        # В обычном режиме тестируем только невыученные слова
        source = [w for w in unique_words if extract_english(w).lower() not in learned]
    
    if not source:
        if revision:
            await bot.send_message(chat_id, "Нет слов для повторения.")
        else:
            await bot.send_message(chat_id, "Все слова уже выучены! Попробуйте завтра.")
        await cb.answer()
        return

    questions = _generate_questions(source, level, chosen_set, revision)
    if not questions:
        await bot.send_message(chat_id, "⚠️ Не удалось создать вопросы.")
        await cb.answer()
        return

    quiz_states[chat_id] = {
        "questions": questions,
        "current": 0,
        "correct": 0,
        "revision": revision,
        "answered": set(),
    }

    await _send_question(chat_id, bot)
    await cb.answer()

async def handle_poll_answer(ans: PollAnswer) -> None:
    """Обрабатывает ответ на вопрос теста."""
    pid = str(ans.poll_id)
    chat_id = poll_to_user.get(pid)
    idx = poll_to_index.get(pid)
    
    if chat_id is None or idx is None or chat_id not in quiz_states:
        logger.warning("Unknown poll id=%s", pid)
        return

    # Удаляем из словарей, чтобы не обрабатывать повторно
    poll_to_user.pop(pid, None)
    poll_to_index.pop(pid, None)

    state = quiz_states.get(chat_id)
    if not state or idx in state["answered"]:
        return
    
    state["answered"].add(idx)
    bot = Bot.get_current()

    q = state["questions"][idx]
    chosen = ans.option_ids[0] if ans.option_ids else None
    text = q["options"][chosen] if chosen is not None else None
    correct = (text == q["correct"])
    logger.info("PollAns chat=%s idx=%d chose=%s ok=%s", chat_id, idx, text, correct)

    # Удаляем предыдущее сообщение с навигацией
    old_msg_id = nav_messages.pop(chat_id, None)
    if old_msg_id:
        try:
            await bot.delete_message(chat_id, old_msg_id)
        except Exception:
            pass

    if correct:
        state["correct"] += 1
        if not q["is_revision"]:
            eng = extract_english(q["word"]).lower()
            if eng not in {extract_english(w[0]).lower() for w in crud.get_learned_words(chat_id)}:
                crud.add_learned_word(
                    chat_id, extract_english(q["word"]), q["correct"],
                    datetime.now().strftime("%Y-%m-%d")
                )

        # Отправляем сообщение о правильном ответе
        await bot.send_message(chat_id, "✅ Верно!")
        
        # Переходим к следующему вопросу
        state["current"] += 1
        if state["current"] >= len(state["questions"]):
            await _finish_quiz(chat_id, bot)
        else:
            await _send_question(chat_id, bot)
    else:
        # Отправляем сообщение о неправильном ответе
        await bot.send_message(
            chat_id,
            f"❌ Неверно. Правильный ответ: {q['correct']}"
        )

        # Отправляем новое сообщение с навигацией и прогрессом
        total_questions = len(state["questions"])
        current_question = idx + 1
        progress_bar = format_progress_bar(current_question, total_questions, 10)
        
        try:
            msg = await bot.send_message(
                chat_id,
                f"📊 Прогресс: {current_question}/{total_questions}\n{progress_bar}",
                reply_markup=_make_nav("quiz")
            )
            nav_messages[chat_id] = msg.message_id
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения с навигацией после неправильного ответа: {e}")

async def process_quiz_navigation(cb: types.CallbackQuery, bot: Bot) -> None:
    """Обрабатывает нажатия на кнопки навигации теста."""
    chat_id = cb.from_user.id
    action = cb.data  # "quiz:back" или "quiz:skip"

    # Удаляем старую навигацию
    old_msg_id = nav_messages.pop(chat_id, None)
    if old_msg_id:
        try:
            await bot.delete_message(chat_id, old_msg_id)
        except Exception:
            pass

    if action == "quiz:back":
        # Завершаем тест и возвращаемся в главное меню
        quiz_states.pop(chat_id, None)
        from keyboards.main_menu import main_menu_keyboard
        await bot.send_message(chat_id, "Тест завершен.", reply_markup=main_menu_keyboard())
        await cb.answer()
        return

    st = quiz_states.get(chat_id)
    if not st:
        await cb.answer("Сессия неактивна.", show_alert=True)
        return

    # Обработка кнопки "Следующее слово" - пропускаем текущий вопрос
    if action == "quiz:skip":
        # Если вопрос еще не отвечен, отмечаем его как отвеченный (но не правильно)
        if st["current"] not in st["answered"]:
            st["answered"].add(st["current"])
        
        # Переходим к следующему вопросу
        st["current"] += 1
        if st["current"] >= len(st["questions"]):
            await _finish_quiz(chat_id, bot)
        else:
            await _send_question(chat_id, bot)
        
        await cb.answer()
        return


def register_quiz_handlers(dp: Dispatcher, bot: Bot) -> None:
    """
    Регистрирует хендлеры для теста «Слова дня».
    """

    # ↳ 1.  ОБРАБОТКА ОТВЕТА НА POLL
    #     фильтруем по таблице poll_to_user, чтобы   QUIZ   ловил ТОЛЬКО свои poll-id
    dp.register_poll_answer_handler(
        handle_poll_answer,
        lambda ans: str(ans.poll_id) in poll_to_user,
    )

    # ↳ 2.  ЗАПУСК ТЕСТА
    dp.register_callback_query_handler(
        lambda cb: asyncio.create_task(start_quiz(cb, bot)),
        lambda cb: cb.data == "quiz:start",
    )

    # ↳ 3.  НАВИГАЦИЯ
    dp.register_callback_query_handler(
        lambda cb: asyncio.create_task(process_quiz_navigation(cb, bot)),
        lambda cb: cb.data in ("quiz:back", "quiz:skip"),
    )