# handlers/quiz.py
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

# --------------------------------------------------------------------------
quiz_states = {}                  # chat_id -> dict(state)
poll_to_user_map = {}             # poll_id -> chat_id
poll_to_question_map = {}         # poll_id -> question_index
active_navigation_messages = {}   # chat_id -> message_id
# --------------------------------------------------------------------------


# ---------------- Генерация вопросов --------------------------------------
def generate_quiz_questions_from_daily(daily_words, level,
                                       chosen_set=None, is_revision=False):
    quiz_data = load_quiz_data(level, chosen_set)
    logger.debug("[GenQ] loaded %s items for level=%s set=%s",
                 len(quiz_data) if quiz_data else 0, level, chosen_set)

    if not quiz_data:
        return []

    mapping = {itm["word"].lower(): itm["translation"] for itm in quiz_data}
    all_translations = [itm["translation"] for itm in quiz_data]
    questions = []

    for src in daily_words:
        key = extract_english(src).lower()
        correct = mapping.get(key) or mapping.get(src.lower())
        if not correct:
            logger.warning("[GenQ] no translation for %s", src)
            continue

        opts, idx = generate_quiz_options(correct, all_translations, 4)
        questions.append({
            "word": src,
            "correct": correct,
            "options": opts,
            "correct_index": idx,
            "is_revision": is_revision,
        })
        logger.debug("[GenQ] %s -> %s (idx=%d)", src, correct, idx)

    return questions
# --------------------------------------------------------------------------


# --------------------- Старт квиза ----------------------------------------
async def start_quiz(callback: types.CallbackQuery, bot: Bot):
    chat_id = callback.from_user.id
    logger.info("[StartQuiz] chat=%s", chat_id)

    # убираем «висящую» навигацию
    if chat_id in active_navigation_messages:
        try:
            await bot.delete_message(chat_id,
                                     active_navigation_messages.pop(chat_id))
        except Exception:
            pass

    # --- получаем пользователя и настройки
    user = crud.get_user(chat_id)
    if not user:
        await bot.send_message(chat_id, "Профиль не найден. Используйте /start.")
        await callback.answer()
        return
    level = user[1]

    try:
        from handlers.settings import user_set_selection
        chosen_set = user_set_selection.get(chat_id)
    except ImportError:
        chosen_set = None

    learned = {extract_english(w[0]).lower()
               for w in crud.get_learned_words(chat_id)}

    # --- берём (или формируем) слова дня
    get_daily_words_for_user(
        chat_id, level, user[2], user[3],
        first_time=REMINDER_START, duration_hours=DURATION_HOURS,
        chosen_set=chosen_set,
    )
    if chat_id not in daily_words_cache:
        await bot.send_message(chat_id, "⚠️ Нет слов для квиза.")
        await callback.answer()
        return

    entry = daily_words_cache[chat_id]
    raw = [m.replace("🔹 ", "").strip() for m in entry[1]]
    if raw and raw[0].startswith(("🎓", "⚠️")):
        raw = raw[1:]

    daily_words = [extract_english(r).lower() for r in raw if r]
    is_revision = len(entry) > 9 and entry[9]

    quiz_source = (
        daily_words if is_revision else [w for w in daily_words if w not in learned]
    )
    if not quiz_source:
        await bot.send_message(chat_id,
                               "Все слова дня уже выучены! Попробуйте завтра.")
        await callback.answer()
        return

    logger.info("[StartQuiz] mode=%s | words=%s",
                "REVISION" if is_revision else "NEW", quiz_source)

    questions = generate_quiz_questions_from_daily(
        quiz_source, level, chosen_set, is_revision
    )
    if not questions:
        await bot.send_message(chat_id, "⚠️ Не удалось создать вопросы.")
        await callback.answer()
        return

    quiz_states[chat_id] = {
        "questions": questions,
        "current_index": 0,
        "correct": 0,
        "is_revision_session": is_revision,
        "answered": set(),
    }

    await send_quiz_question(chat_id, bot)
    await callback.answer()
# --------------------------------------------------------------------------


# ------------------ Отправка вопроса --------------------------------------
async def send_quiz_question(chat_id: int, bot: Bot):
    state = quiz_states.get(chat_id)
    if not state:
        return

    idx = state["current_index"]
    if idx >= len(state["questions"]):
        return

    q = state["questions"][idx]

    # удаляем старую навигацию (если была)
    if chat_id in active_navigation_messages:
        try:
            await bot.delete_message(chat_id,
                                     active_navigation_messages.pop(chat_id))
        except Exception:
            pass

    poll: Poll = await bot.send_poll(
        chat_id=chat_id,
        question=f"Какой перевод слова '{extract_english(q['word'])}'?",
        options=q["options"],
        type="quiz",
        correct_option_id=q["correct_index"],
        explanation=f"Вопрос {idx+1}/{len(state['questions'])}"
                    + (" | Повторение" if q["is_revision"] else ""),
        is_anonymous=False,
    )

    poll_to_user_map[poll.poll.id] = chat_id
    poll_to_question_map[poll.poll.id] = idx
    logger.debug("[SendQ] poll=%s idx=%d correct=%d",
                 poll.poll.id, idx, q["correct_index"])

    # до ответа показываем только «Назад»
    nav = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🔙 Назад", callback_data="quiz:back")
    )
    msg = await bot.send_message(chat_id,
                                 f"Прогресс: {idx+1}/{len(state['questions'])}",
                                 reply_markup=nav)
    active_navigation_messages[chat_id] = msg.message_id
# --------------------------------------------------------------------------


# ------------------ Обработка ответа --------------------------------------
async def handle_poll_answer(poll_answer: PollAnswer):
    bot = Bot.get_current()
    poll_id = poll_answer.poll_id
    chat_id = poll_to_user_map.pop(poll_id, None)
    idx = poll_to_question_map.pop(poll_id, None)

    if chat_id is None or idx is None or chat_id not in quiz_states:
        logger.warning("[PollAns] unknown poll=%s", poll_id)
        return

    state = quiz_states[chat_id]
    if idx in state["answered"]:
        return
    state["answered"].add(idx)

    q = state["questions"][idx]
    chosen = poll_answer.option_ids[0] if poll_answer.option_ids else None
    chosen_text = q["options"][chosen] if chosen is not None else None
    is_ok = chosen_text == q["correct"]

    logger.info("[PollAns] chat=%s idx=%d chosen=%s correct=%s RESULT=%s",
                chat_id, idx, chosen_text, q["correct"],
                "OK" if is_ok else "FAIL")

    if is_ok:
        state["correct"] += 1
        if not q["is_revision"]:
            english = extract_english(q["word"]).lower()
            if english not in {extract_english(w[0]).lower()
                               for w in crud.get_learned_words(chat_id)}:
                crud.add_learned_word(chat_id,
                                      extract_english(q["word"]),
                                      q["correct"],
                                      datetime.now().strftime("%Y-%m-%d"))

    await bot.send_message(chat_id,
                           "✅ Верно!" if is_ok
                           else f"❌ Неверно. Правильный ответ: {q['correct']}")

    # новая навигация: «Назад» + «Дальше»
    if chat_id in active_navigation_messages:
        try:
            await bot.delete_message(chat_id,
                                     active_navigation_messages.pop(chat_id))
        except Exception:
            pass

    nav = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("🔙 Назад", callback_data="quiz:back"),
        InlineKeyboardButton("▶️ Дальше", callback_data="quiz:next"),
    )
    msg = await bot.send_message(
        chat_id,
        f"Ответ обработан. Прогресс: {idx+1}/{len(state['questions'])}",
        reply_markup=nav,
    )
    active_navigation_messages[chat_id] = msg.message_id
# --------------------------------------------------------------------------


# ------------------ Навигация ---------------------------------------------
async def process_quiz_navigation(callback: types.CallbackQuery, bot: Bot):
    chat_id = callback.from_user.id
    act = callback.data

    if chat_id in active_navigation_messages:
        try:
            await bot.delete_message(chat_id,
                                     active_navigation_messages.pop(chat_id))
        except Exception:
            pass

    if act == "quiz:back":
        from keyboards.main_menu import main_menu_keyboard
        quiz_states.pop(chat_id, None)
        await bot.send_message(chat_id, "Возврат в главное меню.",
                               reply_markup=main_menu_keyboard())
        await callback.answer()
        return

    st = quiz_states.get(chat_id)
    if not st:
        await callback.answer("Ошибка состояния квиза.", show_alert=True)
        return
    if st["current_index"] not in st["answered"]:
        await callback.answer("Сначала ответьте на вопрос!", show_alert=True)
        return

    st["current_index"] += 1
    if st["current_index"] >= len(st["questions"]):
        res = format_result_message(st["correct"],
                                    len(st["questions"]),
                                    st["is_revision_session"])
        await bot.send_message(chat_id, res, parse_mode="Markdown")

        if st["correct"] / len(st["questions"]) >= 0.7:
            await send_sticker_with_menu(chat_id, bot,
                                         get_congratulation_sticker())
        else:
            from keyboards.main_menu import main_menu_keyboard
            await bot.send_message(chat_id, "Квиз завершён.",
                                   reply_markup=main_menu_keyboard())
        quiz_states.pop(chat_id, None)
    else:
        await send_quiz_question(chat_id, bot)

    await callback.answer()
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
#  Регистрация хендлеров 
# --------------------------------------------------------------------------
import asyncio
from functools import partial
from aiogram import Dispatcher, Bot

def register_quiz_handlers(dp: Dispatcher, bot: Bot | None = None) -> None:
    """
    Регистрируем хендлеры квиза.
    Аргумент `bot` передаётся из handlers/__init__.py и используется
    внутри лямбда-обёрток, чтобы передать его в coro-функции.
    """
    # Ответы на викторины
    dp.register_poll_answer_handler(handle_poll_answer)

    # Запуск квиза
    dp.register_callback_query_handler(
        lambda cb, b=bot: asyncio.create_task(start_quiz(cb, b)),
        lambda cb: cb.data == "quiz:start",
    )

    # Навигация «Назад» / «Дальше»
    dp.register_callback_query_handler(
        lambda cb, b=bot: asyncio.create_task(process_quiz_navigation(cb, b)),
        lambda cb: cb.data in ("quiz:back", "quiz:next"),
    )
# --------------------------------------------------------------------------
