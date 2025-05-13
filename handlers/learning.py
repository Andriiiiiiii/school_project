# handlers/learning.py
"""
Раздел «Обучение»
▪ Тест по словарю (dtest)
▪ Заучивание сета (mtest)

Работает через встроенные Telegram-quiz-poll.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Poll, PollAnswer

from config import DEFAULT_SETS, LEVELS_DIR
from database import crud
from keyboards.main_menu import main_menu_keyboard
from keyboards.submenus import learning_menu_keyboard
from utils.helpers import extract_english
from utils.quiz_helpers import load_quiz_data
from utils.quiz_utils import generate_quiz_options
from utils.sticker_helper import get_congratulation_sticker, send_sticker_with_menu
from utils.visual_helpers import format_progress_bar

logger = logging.getLogger(__name__)

# ───────────────────────── helpers ──────────────────────────
_RX_SPACES    = re.compile(r"\s+")
_RX_VARIANTS  = re.compile(r"[;,/]|(?:\s+или\s+)", re.I)


def _normalize(txt: str) -> str:
    return _RX_SPACES.sub(" ", txt.strip().lower()).replace("ё", "е")


def _is_correct(chosen: str | None, correct: str | None) -> bool:
    if not chosen or not correct:
        return False
    chosen_n = _normalize(chosen)
    variants = [_normalize(v) for v in _RX_VARIANTS.split(correct) if v.strip()]
    return chosen_n in variants or chosen_n == _normalize(correct)


def _get_user_val(user: tuple, idx: int, default: Any) -> Any:
    return user[idx] if len(user) > idx and user[idx] is not None else default


def _read_set_words(level: str, name: str) -> List[str]:
    file = Path(LEVELS_DIR) / level / f"{name}.txt"
    if not file.exists():
        raise FileNotFoundError(file)
    for enc in ("utf-8", "cp1251", "latin-1", "iso-8859-1"):
        try:
            return [ln.strip() for ln in file.read_text(enc).splitlines() if ln.strip()]
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(f"Can't decode {file}")


def _make_nav(prefix: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🛑 Закончить",  callback_data=f"{prefix}:back"),
        InlineKeyboardButton("⏭️ Следующее", callback_data=f"{prefix}:skip"),
    )
    return kb

# ───────────────────────── state ────────────────────────────
@dataclass
class LearningState:
    questions: List[Dict[str, Any]]
    prefix: str
    current: int = 0
    correct: int = 0
    answered: set[int] = field(default_factory=set)


states: Dict[int, LearningState] = {}

#   ключевые таблицы ТОЛЬКО для «Обучения»
lpoll2user: Dict[str, int] = {}
lpoll2idx:  Dict[str, int] = {}
lnav_msgs:  Dict[int, int] = {}

# ───────────────────────── builders ─────────────────────────
def _make_question_list(
    words: List[str],
    translations_map: Dict[str, str],
    all_trans: List[str],
    revision_flags: Dict[str, bool],
) -> List[Dict[str, Any]]:
    res: List[Dict[str, Any]] = []
    for src in words:
        eng = extract_english(src)
        rus = translations_map.get(eng.lower())
        if not rus:
            for sep in (" - ", " – ", ": "):
                if sep in src:
                    rus = src.split(sep, 1)[1].strip()
                    break
        if not rus:
            logger.warning("Learning: skip «%s» (нет перевода)", src)
            continue
        rus = rus.strip()
        opts, _ = generate_quiz_options(rus, all_trans, 4)
        opts = [o.strip() for o in opts]
        idx = opts.index(rus) if rus in opts else 0
        opts[0], opts[idx] = opts[idx], opts[0]  # гарантируем наличие правильного
        res.append(
            dict(
                word=eng,
                correct=rus,
                options=opts,
                correct_index=opts.index(rus),
                is_revision=revision_flags.get(eng.lower(), False),
            )
        )
    return res


def build_dict_test(chat: int, user: tuple) -> List[Dict[str, Any]]:
    learned = crud.get_learned_words(chat)
    if not learned:
        return []
    count = min(_get_user_val(user, 7, 5), len(learned))
    sample = random.sample(learned, count)
    level, chosen_set = user[1], _get_user_val(user, 6, None)
    quiz_data = load_quiz_data(level, chosen_set)
    all_tr = [d["translation"].strip() for d in quiz_data]
    return _make_question_list(
        [eng for eng, _ in sample],
        {eng.lower(): rus.strip() for eng, rus in sample},
        all_tr,
        {extract_english(e).lower(): True for e, _ in sample},
    )


def build_memorize(chat: int, user: tuple) -> List[Dict[str, Any]]:
    level = user[1]
    chosen_set = _get_user_val(user, 6, None) or DEFAULT_SETS.get(level)
    set_words = _read_set_words(level, chosen_set)
    count = min(_get_user_val(user, 8, 5), len(set_words))
    sample = random.sample(set_words, count)
    quiz_data = load_quiz_data(level, chosen_set)
    translations = {d["word"].lower(): d["translation"].strip() for d in quiz_data}
    all_tr = [d["translation"].strip() for d in quiz_data]
    learned = {extract_english(w[0]).lower() for w in crud.get_learned_words(chat)}
    return _make_question_list(
        sample, translations, all_tr, {w: w in learned for w in translations}
    )

# ───────────────────────── runtime helpers ──────────────────
async def _delete_nav(bot: Bot, chat: int) -> None:
    mid = lnav_msgs.pop(chat, None)
    if mid:
        try:
            await bot.delete_message(chat, mid)
        except Exception:
            pass


async def _send_question(chat: int, bot: Bot) -> None:
    st = states.get(chat)
    if not st:
        return
    if st.current >= len(st.questions):
        return await _finish(chat, bot)

    q = st.questions[st.current]
    poll: Poll = await bot.send_poll(
        chat_id=chat,
        question=f"Перевод слова «{extract_english(q['word'])}»?",
        options=q["options"],
        type="quiz",
        correct_option_id=q["correct_index"],
        explanation=f"Вопрос {st.current + 1}/{len(st.questions)}",
        is_anonymous=False,
    )
    pid = str(poll.poll.id)
    lpoll2user[pid] = chat
    lpoll2idx[pid] = st.current
    logger.debug("Learning: send poll %s ➜ chat=%s idx=%d | lpoll2user=%s",
                 pid, chat, st.current, lpoll2user)

    await _delete_nav(bot, chat)
    bar = format_progress_bar(st.current + 1, len(st.questions), 10)
    msg = await bot.send_message(
        chat,
        f"📊 Прогресс: {st.current + 1}/{len(st.questions)}\n{bar}",
        reply_markup=_make_nav(st.prefix),
        parse_mode="HTML",
    )
    lnav_msgs[chat] = msg.message_id


async def _finish(chat: int, bot: Bot) -> None:
    st = states.pop(chat, None)
    if not st:
        return
    await _delete_nav(bot, chat)
    total = len(st.questions)
    perc = st.correct / total * 100 if total else 0
    bar = format_progress_bar(st.correct, total, 20)
    title = ("📚 Тест по словарю завершён!"
             if st.prefix == "dtest" else "📝 Заучивание сета завершено!")
    text = f"{title}\n\n*Счёт:* {st.correct}/{total} ({perc:.1f} %)\n{bar}"
    if perc < 70:
        text += "\n\n💡 Повторяйте слова чаще."
    await bot.send_message(chat, text, parse_mode="Markdown")
    if perc >= 70:
        await send_sticker_with_menu(chat, bot, get_congratulation_sticker())
    else:
        await bot.send_message(chat, "Тест завершён.", reply_markup=main_menu_keyboard())

# ───────────────────────── poll-answer ───────────────────────
async def poll_answer_handler(ans: PollAnswer) -> None:
    pid = str(ans.poll_id)
    chat = lpoll2user.get(pid)
    qidx = lpoll2idx.get(pid)

    logger.debug("Learning: poll_answer %s | in_table=%s lpoll2user=%s",
                 pid, pid in lpoll2user, lpoll2user)

    if chat is None or qidx is None or chat not in states:
        return  # чужой poll

    lpoll2user.pop(pid, None)
    lpoll2idx.pop(pid, None)

    st = states[chat]
    if qidx in st.answered:
        return
    st.answered.add(qidx)

    q = st.questions[qidx]
    chosen_idx = ans.option_ids[0] if ans.option_ids else None
    chosen_txt = q["options"][chosen_idx] if chosen_idx is not None else None
    ok = _is_correct(chosen_txt, q["correct"])

    logger.debug("Learning: chat=%s qidx=%d chosen=%s correct=%s ok=%s",
                 chat, qidx, chosen_txt, q["correct"], ok)

    bot = Bot.get_current()
    await _delete_nav(bot, chat)

    if ok:
        st.correct += 1
        await bot.send_message(chat, "✅ Верно!")
        st.current += 1
        await _send_question(chat, bot)
    else:
        await bot.send_message(chat, f"❌ Неверно. Правильный ответ: {q['correct']}")
        bar = format_progress_bar(qidx + 1, len(st.questions), 10)
        msg = await bot.send_message(
            chat,
            f"📊 Прогресс: {qidx + 1}/{len(st.questions)}\n{bar}",
            reply_markup=_make_nav(st.prefix),
            parse_mode="HTML",
        )
        lnav_msgs[chat] = msg.message_id

# ───────────────────────── nav buttons ───────────────────────
async def nav_callback(cb: types.CallbackQuery, bot: Bot) -> None:
    chat = cb.from_user.id
    _, cmd = cb.data.split(":", 1)
    await _delete_nav(bot, chat)

    if cmd == "back":
        states.pop(chat, None)
        await bot.send_message(chat, "Возврат в главное меню.", reply_markup=main_menu_keyboard())
        return await cb.answer()

    st = states.get(chat)
    if not st:
        return await cb.answer("Сессия неактивна.", show_alert=True)

    if cmd == "skip":
        if st.current not in st.answered:
            st.answered.add(st.current)
        st.current += 1
        await _send_question(chat, bot)
        return await cb.answer()

# ───────────────────────── start helpers ─────────────────────
async def _start(cb: types.CallbackQuery, bot: Bot, builder):
    chat = cb.from_user.id
    user = crud.get_user(chat)
    if not user:
        return await cb.answer("Профиль не найден.", show_alert=True)

    questions = builder(chat, user)
    if not questions:
        return await cb.answer("Нет данных для теста.", show_alert=True)

    prefix = "dtest" if builder is build_dict_test else "mtest"
    states[chat] = LearningState(questions=questions, prefix=prefix)
    logger.debug("Learning: new session chat=%s prefix=%s qs=%d", chat, prefix, len(questions))

    await cb.answer()
    await _send_question(chat, bot)

# ───────────────────────── registration ──────────────────────
def register_learning_handlers(dp: Dispatcher, bot: Bot | None = None) -> None:

    # 1) ответ на poll  ▼   обрабатываем ТОЛЬКО если poll-id в таблице
    dp.register_poll_answer_handler(
        poll_answer_handler,
        lambda ans: str(ans.poll_id) in lpoll2user,
    )

    # 2) запуск двух режимов
    dp.register_callback_query_handler(
        lambda cb: asyncio.create_task(_start(cb, bot, build_dict_test)),
        lambda cb: cb.data == "learning:dictionary_test",
    )
    dp.register_callback_query_handler(
        lambda cb: asyncio.create_task(_start(cb, bot, build_memorize)),
        lambda cb: cb.data == "learning:memorize_set",
    )

    # 3) навигация
    dp.register_callback_query_handler(
        lambda cb: asyncio.create_task(nav_callback(cb, bot)),
        lambda cb: cb.data.startswith(("dtest:", "mtest:")),
    )

    # меню «Обучение»
    dp.register_callback_query_handler(
        lambda cb: cb.message.edit_text("📚 Выберите режим обучения:",
                                        reply_markup=learning_menu_keyboard()),
        lambda cb: cb.data == "menu:learning",
    )
