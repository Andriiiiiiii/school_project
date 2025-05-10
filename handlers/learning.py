# handlers/learning.py
"""
Раздел «Обучение»: 
▪ Тест по словарю («dtest»)
▪ Заучивание сета («mtest»)

Работает через встроенные Telegram-quiz-poll.
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Poll, PollAnswer

from config import DEFAULT_SETS, LEVELS_DIR
from database import crud
from keyboards.main_menu import main_menu_keyboard
from keyboards.submenus import learning_menu_keyboard, learning_settings_keyboard
from utils.helpers import extract_english
from utils.quiz_helpers import load_quiz_data
from utils.quiz_utils import generate_quiz_options
from utils.sticker_helper import get_congratulation_sticker, send_sticker_with_menu
from utils.visual_helpers import format_progress_bar

logger = logging.getLogger(__name__)

# ────────────────────────────── service ────────────────────────────────────


def _get_user_val(user: tuple, idx: int, default: Any) -> Any:
    """Безопасно достаём значение из tuple-пользователя."""
    return user[idx] if len(user) > idx and user[idx] is not None else default


def _read_set_words(level: str, name: str) -> List[str]:
    """Читает txt-сет (поддержка нескольких кодировок)."""
    file = Path(LEVELS_DIR) / level / f"{name}.txt"
    if not file.exists():
        raise FileNotFoundError(file)

    for enc in ("utf-8", "cp1251", "latin-1", "iso-8859-1"):
        try:
            return [ln.strip() for ln in file.read_text(enc).splitlines() if ln.strip()]
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(f"Can't decode {file}")


def _nav(prefix: str, forward: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data=f"{prefix}:back"))
    if forward:
        kb.add(InlineKeyboardButton("▶️ Дальше", callback_data=f"{prefix}:next"))
    return kb


# ────────────────────────────── state ║ cache ──────────────────────────────
@dataclass
class LearningState:
    questions: List[Dict[str, Any]]
    prefix: str                                   # dtest | mtest
    current: int = 0
    correct: int = 0
    answered: set[int] = field(default_factory=set)


states: Dict[int, LearningState] = {}
poll2user: Dict[str, int] = {}
poll2qidx: Dict[str, int] = {}
nav_msgs: Dict[int, int] = {}

# ────────────────────────────── question builders ─────────────────────────


def _make_question_list(
    words: List[str],
    translations_map: Dict[str, str],
    all_trans: List[str],
    revision_flags: Dict[str, bool],
) -> List[Dict]:
    q = []
    for w in words:
        eng = extract_english(w)
        rus = translations_map.get(eng.lower())
        if not rus:                                       # fallback к формату “eng – rus”
            for sep in (" - ", " – ", ": "):
                if sep in w:
                    rus = w.split(sep, 1)[1].strip()
                    break
        if not rus:
            continue
        opts, idx = generate_quiz_options(rus, all_trans, 4)
        q.append(
            dict(
                word=eng,
                correct=rus,
                options=opts,
                correct_index=idx,
                is_revision=revision_flags.get(eng.lower(), False),
            )
        )
    return q


def build_dict_test(chat: int, user: tuple) -> List[Dict]:
    learned = crud.get_learned_words(chat)
    if not learned:
        return []

    count = min(_get_user_val(user, 7, 5), len(learned))
    sample = random.sample(learned, count)                # (eng, rus)

    level, chosen_set = user[1], _get_user_val(user, 6, None)
    quiz_data = load_quiz_data(level, chosen_set)
    if not quiz_data:
        return []

    all_tr = [d["translation"] for d in quiz_data]
    return _make_question_list(
        [eng for eng, _ in sample],
        {eng.lower(): rus for eng, rus in sample},
        all_tr,
        {extract_english(e).lower(): True for e, _ in sample},
    )


def build_memorize(chat: int, user: tuple) -> List[Dict]:
    level = user[1]
    chosen_set = _get_user_val(user, 6, None) or DEFAULT_SETS.get(level)
    set_words = _read_set_words(level, chosen_set)

    count = min(_get_user_val(user, 8, 5), len(set_words))
    sample = random.sample(set_words, count)

    quiz_data = load_quiz_data(level, chosen_set)
    translations = {d["word"].lower(): d["translation"] for d in quiz_data}
    all_tr = [d["translation"] for d in quiz_data]

    learned = {
        extract_english(w[0]).lower() for w in crud.get_learned_words(chat)
    }
    return _make_question_list(sample, translations, all_tr, {w: w in learned for w in translations})


# ────────────────────────────── core helpers ──────────────────────────────
async def _delete_safe(bot: Bot, chat: int):
    """Удаляет активный нав-сообщение, если есть."""
    if chat in nav_msgs:
        try:
            await bot.delete_message(chat, nav_msgs.pop(chat))
        except Exception:
            pass


async def _send_question(chat: int, bot: Bot):
    st = states.get(chat)
    if not st:
        return
    if st.current >= len(st.questions):
        await _finish(chat, bot)
        return

    q = st.questions[st.current]
    await _delete_safe(bot, chat)

    poll: Poll = await bot.send_poll(
        chat_id=chat,
        question=f"Перевод слова «{extract_english(q['word'])}»?",
        options=q["options"],
        type="quiz",
        correct_option_id=q["correct_index"],
        explanation=f"Вопрос {st.current+1}/{len(st.questions)}",
        explanation_parse_mode="html",
        is_anonymous=False,
    )
    pid = str(poll.poll.id)
    poll2user[pid] = chat
    poll2qidx[pid] = st.current

    msg = await bot.send_message(
        chat, f"Прогресс: {st.current+1}/{len(st.questions)}", reply_markup=_nav(st.prefix)
    )
    nav_msgs[chat] = msg.message_id


async def _finish(chat: int, bot: Bot):
    st = states.pop(chat, None)
    if not st:
        return

    total = len(st.questions)
    perc = st.correct / total * 100 if total else 0
    header = "📚 Тест по словарю завершён!" if st.prefix == "dtest" else "📝 Заучивание сета завершено!"
    bar = format_progress_bar(st.correct, total, 20)

    txt = f"{header}\n\n*Счёт:* {st.correct}/{total} ({perc:.1f} %)\n{bar}\n\n"
    if perc < 70:
        txt += "💡 Повторяйте слова чаще для лучшего запоминания."

    await bot.send_message(chat, txt, parse_mode="Markdown")
    dest_menu = send_sticker_with_menu if perc >= 70 else bot.send_message
    await dest_menu(chat, "Тест завершён.", reply_markup=main_menu_keyboard())

    await _delete_safe(bot, chat)


# ────────────────────────────── handlers ──────────────────────────────────
async def poll_answer_handler(ans: PollAnswer):
    pid = str(ans.poll_id)
    if pid not in poll2user:                      # чужой PollAnswer
        return

    bot = Bot.get_current()
    chat, qidx = poll2user.pop(pid), poll2qidx.pop(pid)
    st = states.get(chat)
    if not st or qidx in st.answered:
        return
    st.answered.add(qidx)

    q = st.questions[qidx]
    chosen = ans.option_ids[0] if ans.option_ids else None
    ok = chosen == q["correct_index"]
    st.correct += int(ok)

    logger.debug("[Learning] chat=%s idx=%d ok=%s", chat, qidx, ok)

    await bot.send_message(
        chat, "✅ Верно!" if ok else f"❌ Неверно. Правильный ответ: {q['correct']}"
    )

    await _delete_safe(bot, chat)
    msg = await bot.send_message(
        chat,
        f"Ответ обработан. Прогресс: {qidx+1}/{len(st.questions)}",
        reply_markup=_nav(st.prefix, True),
    )
    nav_msgs[chat] = msg.message_id


async def nav_callback(cb: types.CallbackQuery, bot: Bot):
    chat = cb.from_user.id
    _, cmd = cb.data.split(":", 1)

    await _delete_safe(bot, chat)

    if cmd == "back":
        states.pop(chat, None)
        await bot.send_message(chat, "Возврат в главное меню.", reply_markup=main_menu_keyboard())
        return await cb.answer()

    st = states.get(chat)
    if not st or st.current not in st.answered:
        return await cb.answer("Сначала ответьте на вопрос!", show_alert=True)

    st.current += 1
    await _send_question(chat, bot)
    await cb.answer()


# ────────────────────────────── start helpers ─────────────────────────────
async def _start(cb: types.CallbackQuery, bot: Bot, builder):
    chat = cb.from_user.id
    user = crud.get_user(chat)
    if not user:
        return await cb.answer("Профиль не найден.", show_alert=True)

    try:
        qs = builder(chat, user)
    except Exception as e:                        # чтение сета и т.п.
        logger.exception(e)
        return await cb.answer("Ошибка формирования вопросов.", show_alert=True)

    if not qs:
        return await cb.answer("Нет данных для теста.", show_alert=True)

    prefix = "dtest" if builder is build_dict_test else "mtest"
    states[chat] = LearningState(questions=qs, prefix=prefix)
    await cb.answer()
    await _send_question(chat, bot)


# ────────────────────────────── registration ──────────────────────────────
def register_learning_handlers(dp: Dispatcher, bot: Bot | None = None) -> None:
    """Подключает все хендлеры раздела «Обучение»."""

    # ответы на poll-quiz
    dp.register_poll_answer_handler(poll_answer_handler)

    # запуск режимов
    dp.register_callback_query_handler(
        lambda cb, b=bot: asyncio.create_task(_start(cb, b, build_dict_test)),
        lambda cb: cb.data == "learning:dictionary_test",
    )
    dp.register_callback_query_handler(
        lambda cb, b=bot: asyncio.create_task(_start(cb, b, build_memorize)),
        lambda cb: cb.data == "learning:memorize_set",
    )

    # навигация
    dp.register_callback_query_handler(
        lambda cb, b=bot: asyncio.create_task(nav_callback(cb, b)),
        lambda cb: cb.data.startswith(("dtest:", "mtest:")),
    )

    # меню / настройки
    dp.register_callback_query_handler(
        lambda cb: asyncio.create_task(
            cb.message.edit_text("📚 Выберите режим обучения:", reply_markup=learning_menu_keyboard())
        ),
        lambda cb: cb.data == "menu:learning",
    )
    dp.register_callback_query_handler(
        lambda cb: asyncio.create_task(
            cb.message.edit_text("⚙️ Настройки обучения:", reply_markup=learning_settings_keyboard())
        ),
        lambda cb: cb.data == "learning:settings",
    )
