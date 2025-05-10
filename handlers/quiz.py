# handlers/quiz.py
"""
Квиз «Слова дня»: встроенные quiz-поллы с навигацией.
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
from utils.visual_helpers import extract_english, format_result_message

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────
#   Глобальное состояние
# ───────────────────────────────────────────────────────────────
quiz_states: dict[int, dict] = {}
poll_to_user: dict[str, int] = {}
poll_to_index: dict[str, int] = {}
nav_messages: dict[int, int] = {}
# ───────────────────────────────────────────────────────────────


def _make_nav(prefix: str, allow_next: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data=f"{prefix}:back"))
    if allow_next:
        kb.add(InlineKeyboardButton("▶️ Дальше", callback_data=f"{prefix}:next"))
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


async def start_quiz(cb: types.CallbackQuery, bot: Bot) -> None:
    chat_id = cb.from_user.id
    logger.info("StartQuiz chat=%s", chat_id)

    # Убираем старую навигацию
    if nav_messages.get(chat_id):
        try:
            await bot.delete_message(chat_id, nav_messages.pop(chat_id))
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
        await bot.send_message(chat_id, "⚠️ Нет слов для квиза.")
        await cb.answer()
        return

    raw = [m.replace("🔹 ", "").strip() for m in entry[1]]
    if raw and raw[0].startswith(("🎓", "⚠️")):
        raw.pop(0)

    daily = [extract_english(r).lower() for r in raw if r]
    revision = bool(len(entry) > 9 and entry[9])
    source = daily if revision else [w for w in daily if w not in learned]
    if not source:
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


async def _send_question(chat_id: int, bot: Bot) -> None:
    state = quiz_states.get(chat_id)
    if not state:
        return

    idx = state["current"]
    if idx >= len(state["questions"]):
        return

    q = state["questions"][idx]
    # Удаляем предыдущую навигацию
    if nav_messages.get(chat_id):
        try:
            await bot.delete_message(chat_id, nav_messages.pop(chat_id))
        except Exception:
            pass

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

    msg = await bot.send_message(
        chat_id,
        f"Прогресс: {idx+1}/{len(state['questions'])}",
        reply_markup=_make_nav("quiz", allow_next=False)
    )
    nav_messages[chat_id] = msg.message_id


async def handle_poll_answer(ans: PollAnswer) -> None:
    pid = str(ans.poll_id)
    chat_id = poll_to_user.pop(pid, None)
    idx = poll_to_index.pop(pid, None)
    if chat_id is None or idx is None or chat_id not in quiz_states:
        logger.warning("Unknown poll id=%s", pid)
        return

    state = quiz_states[chat_id]
    if idx in state["answered"]:
        return
    state["answered"].add(idx)

    q = state["questions"][idx]
    chosen = ans.option_ids[0] if ans.option_ids else None
    text = q["options"][chosen] if chosen is not None else None
    correct = (text == q["correct"])
    logger.info("PollAns chat=%s idx=%d chose=%s ok=%s", chat_id, idx, text, correct)

    if correct:
        state["correct"] += 1
        if not q["is_revision"]:
            eng = extract_english(q["word"]).lower()
            if eng not in {extract_english(w[0]).lower() for w in crud.get_learned_words(chat_id)}:
                crud.add_learned_word(
                    chat_id, extract_english(q["word"]), q["correct"],
                    datetime.now().strftime("%Y-%m-%d")
                )

    await Bot.get_current().send_message(
        chat_id,
        "✅ Верно!" if correct else f"❌ Неверно. Правильный ответ: {q['correct']}"
    )

    # Новая навигация «Назад/Дальше»
    if nav_messages.get(chat_id):
        try:
            await Bot.get_current().delete_message(chat_id, nav_messages.pop(chat_id))
        except Exception:
            pass

    msg = await Bot.get_current().send_message(
        chat_id,
        f"Ответ обработан. Прогресс: {idx+1}/{len(state['questions'])}",
        reply_markup=_make_nav("quiz", allow_next=True)
    )
    nav_messages[chat_id] = msg.message_id


async def process_quiz_navigation(cb: types.CallbackQuery, bot: Bot) -> None:
    chat_id = cb.from_user.id
    action = cb.data  # "quiz:back" или "quiz:next"

    # удаляем старую навигацию
    if nav_messages.get(chat_id):
        try:
            await bot.delete_message(chat_id, nav_messages.pop(chat_id))
        except Exception:
            pass

    if action == "quiz:back":
        quiz_states.pop(chat_id, None)
        from keyboards.main_menu import main_menu_keyboard
        await bot.send_message(chat_id, "Возврат в главное меню.", reply_markup=main_menu_keyboard())
        await cb.answer()
        return

    st = quiz_states.get(chat_id)
    if not st:
        await cb.answer("Сессия неактивна.", show_alert=True)
        return
    if st["current"] not in st["answered"]:
        await cb.answer("Сначала ответьте на текущий вопрос!", show_alert=True)
        return

    st["current"] += 1
    if st["current"] >= len(st["questions"]):
        # Финал
        correct, total = st["correct"], len(st["questions"])
        result = format_result_message(correct, total, st["revision"])
        await bot.send_message(chat_id, result, parse_mode="Markdown")
        if correct / total >= 0.7:
            await send_sticker_with_menu(chat_id, bot, get_congratulation_sticker())
        else:
            from keyboards.main_menu import main_menu_keyboard
            await bot.send_message(chat_id, "Квиз завершён.", reply_markup=main_menu_keyboard())
        quiz_states.pop(chat_id, None)
    else:
        await _send_question(chat_id, bot)

    await cb.answer()


def register_quiz_handlers(dp: Dispatcher, bot: Bot) -> None:
    """
    Регистрирует хендлеры для квиза «Слова дня».
    """
    # Только свои PollAnswer
    dp.register_poll_answer_handler(
        handle_poll_answer,
        lambda ans: str(ans.poll_id) in poll_to_user
    )

    # Запуск
    dp.register_callback_query_handler(
        lambda cb: asyncio.create_task(start_quiz(cb, bot)),
        lambda cb: cb.data == "quiz:start"
    )

    # Навигация «Назад/Дальше»
    dp.register_callback_query_handler(
        lambda cb: asyncio.create_task(process_quiz_navigation(cb, bot)),
        lambda cb: cb.data in ("quiz:back", "quiz:next")
    )
