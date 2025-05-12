# handlers/learning.py
"""
Раздел «Обучение»
▪ Тест по словарю («dtest»)
▪ Заучивание сета («mtest»)

Работает через встроенные Telegram-quiz-poll.
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
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


def _make_nav(prefix: str) -> InlineKeyboardMarkup:
    """Клавиатура навигации (два варианта)."""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🛑 Закончить",    callback_data=f"{prefix}:back"),
        InlineKeyboardButton("⏭️ Следующее",   callback_data=f"{prefix}:skip"),
    )
    return kb

# ────────────────────────────── state ║ cache ──────────────────────────────
@dataclass
class LearningState:
    questions: List[Dict[str, Any]]
    prefix: str                  # dtest | mtest
    current: int = 0
    correct: int = 0
    answered: set[int] = field(default_factory=set)


states: Dict[int, LearningState] = {}
poll2user: Dict[str, int] = {}   # poll_id → chat_id
poll2qidx: Dict[str, int] = {}   # poll_id → index в списке вопросов
nav_msgs: Dict[int, int] = {}    # chat_id → message_id нав-сообщения

# ────────────────────────────── question builders ─────────────────────────
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
        if not rus:                                 # fallback «eng – rus»
            for sep in (" - ", " – ", ": "):
                if sep in src:
                    rus = src.split(sep, 1)[1].strip()
                    break
        if not rus:
            continue

        opts, idx = generate_quiz_options(rus, all_trans, 4)
        res.append(
            dict(
                word=eng,
                correct=rus,
                options=opts,
                correct_index=idx,
                is_revision=revision_flags.get(eng.lower(), False),
            )
        )
    return res


def build_dict_test(chat: int, user: tuple) -> List[Dict[str, Any]]:
    """Сбор вопросов для режима «dtest»."""
    learned = crud.get_learned_words(chat)
    if not learned:
        return []

    count = min(_get_user_val(user, 7, 5), len(learned))
    sample = random.sample(learned, count)  # (eng, rus)

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


def build_memorize(chat: int, user: tuple) -> List[Dict[str, Any]]:
    """Сбор вопросов для режима «mtest»."""
    level = user[1]
    chosen_set = _get_user_val(user, 6, None) or DEFAULT_SETS.get(level)
    set_words = _read_set_words(level, chosen_set)

    count = min(_get_user_val(user, 8, 5), len(set_words))
    sample = random.sample(set_words, count)

    quiz_data = load_quiz_data(level, chosen_set)
    translations = {d["word"].lower(): d["translation"] for d in quiz_data}
    all_tr = [d["translation"] for d in quiz_data]

    learned = {extract_english(w[0]).lower() for w in crud.get_learned_words(chat)}
    return _make_question_list(
        sample, translations, all_tr, {w: w in learned for w in translations}
    )

# ────────────────────────────── helpers ────────────────────────────────────
async def _delete_nav(bot: Bot, chat: int) -> None:
    """Удаляет активное нав-сообщение, если есть."""
    msg_id = nav_msgs.pop(chat, None)
    if msg_id:
        try:
            await bot.delete_message(chat, msg_id)
        except Exception:
            pass


async def _send_question(chat: int, bot: Bot) -> None:
    """Отправляет очередной вопрос с навигацией."""
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
        explanation=f"Вопрос {st.current+1}/{len(st.questions)}",
        is_anonymous=False,
    )
    pid = str(poll.poll.id)               # ← ВСЕГДА str !
    poll2user[pid] = chat
    poll2qidx[pid] = st.current
    logger.debug("Learning: sent poll pid=%s chat=%s idx=%d", pid, chat, st.current)

    # прогресс + кнопки
    await _delete_nav(bot, chat)
    bar = format_progress_bar(st.current + 1, len(st.questions), 10)
    msg = await bot.send_message(
        chat, f"📊 Прогресс: {st.current+1}/{len(st.questions)}\n{bar}",
        reply_markup=_make_nav(st.prefix),
    )
    nav_msgs[chat] = msg.message_id


async def _finish(chat: int, bot: Bot) -> None:
    """Финальный экран результатов."""
    st = states.pop(chat, None)
    if not st:
        return

    await _delete_nav(bot, chat)
    total = len(st.questions)
    perc = st.correct / total * 100 if total else 0
    header = "📚 Тест по словарю завершён!" if st.prefix == "dtest" else "📝 Заучивание сета завершено!"
    bar = format_progress_bar(st.correct, total, 20)

    text = f"{header}\n\n*Счёт:* {st.correct}/{total} ({perc:.1f} %)\n{bar}\n"
    if perc < 70:
        text += "\n💡 Повторяйте слова чаще."

    await bot.send_message(chat, text, parse_mode="Markdown")

    if perc >= 70:
        await send_sticker_with_menu(chat, bot, get_congratulation_sticker())
    else:
        await bot.send_message(chat, "Тест завершён.", reply_markup=main_menu_keyboard())

# ────────────────────────────── handlers ──────────────────────────────────
async def poll_answer_handler(ans: PollAnswer) -> None:
    """Обрабатывает ответ в обучении."""
    pid = str(ans.poll_id)            # ← str обязательно
    chat = poll2user.get(pid)
    qidx = poll2qidx.get(pid)

    if chat is None or qidx is None or chat not in states:
        logger.warning("Learning: unknown poll id=%s", pid)
        return

    # убираем из словарей → не обрабатываем повторно
    poll2user.pop(pid, None)
    poll2qidx.pop(pid, None)

    st = states.get(chat)
    if not st or qidx in st.answered:
        return
    st.answered.add(qidx)

    q = st.questions[qidx]
    chosen_idx = ans.option_ids[0] if ans.option_ids else None
    chosen_txt = q["options"][chosen_idx] if chosen_idx is not None else None
    ok = (chosen_txt == q["correct"])

    if ok:
        st.correct += 1

    bot = Bot.get_current()
    await _delete_nav(bot, chat)

    if ok:
        await bot.send_message(chat, "✅ Верно!")
        st.current += 1
        await _send_question(chat, bot)
    else:
        await bot.send_message(chat, f"❌ Неверно. Правильный ответ: {q['correct']}")
        bar = format_progress_bar(qidx + 1, len(st.questions), 10)
        msg = await bot.send_message(
            chat, f"📊 Прогресс: {qidx+1}/{len(st.questions)}\n{bar}",
            reply_markup=_make_nav(st.prefix),
        )
        nav_msgs[chat] = msg.message_id

# ────────────────────────────── nav buttons ───────────────────────────────
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

# ────────────────────────────── learning settings ─────────────────────────
# (оставлены без изменений – ошибок не было)

# ────────────────────────────── start helpers ─────────────────────────────
async def _start(cb: types.CallbackQuery, bot: Bot, builder):
    """Запускает тест указанного типа."""
    chat = cb.from_user.id
    user = crud.get_user(chat)
    if not user:
        return await cb.answer("Профиль не найден.", show_alert=True)

    try:
        qs = builder(chat, user)
    except Exception as e:
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
    # ответы poll
    dp.register_poll_answer_handler(
        poll_answer_handler,
        lambda ans: str(ans.poll_id) in poll2user,   # фильтр по нашему dict
    )
    
    # запуск режимов
    dp.register_callback_query_handler(
        lambda cb: asyncio.create_task(_start(cb, bot, build_dict_test)),
        lambda cb: cb.data == "learning:dictionary_test",
    )
    dp.register_callback_query_handler(
        lambda cb: asyncio.create_task(_start(cb, bot, build_memorize)),
        lambda cb: cb.data == "learning:memorize_set",
    )

    # навигация
    dp.register_callback_query_handler(
        lambda cb: asyncio.create_task(nav_callback(cb, bot)),
        lambda cb: cb.data.startswith(("dtest:", "mtest:")),
    )

    # меню
    dp.register_callback_query_handler(
        lambda cb: cb.message.edit_text("📚 Выберите режим обучения:", reply_markup=learning_menu_keyboard()),
        lambda cb: cb.data == "menu:learning",
    )

    # настройки – остаются как были
    dp.register_callback_query_handler(
        lambda cb: asyncio.create_task(handle_learning_settings(cb, bot)),
        lambda cb: cb.data in ("learning:test_settings", "learning:memorize_settings")
                    or cb.data.startswith(("set_test_words:", "set_memorize_words:")),
    )
