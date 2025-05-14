"""
handlers/learning.py — раздел «Обучение»
• dtest – тест по словарю
• mtest – заучивание сета
• learning settings – настройка количества слов в режимах
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
from keyboards.submenus import (
    learning_menu_keyboard,
    learning_settings_keyboard,  # базовый: две кнопки «Настройки теста/заучивания» + «Назад»
)
from utils.helpers import extract_english
from utils.quiz_helpers import load_quiz_data
from utils.quiz_utils import generate_quiz_options
from utils.sticker_helper import get_congratulation_sticker, send_sticker_with_menu
from utils.visual_helpers import format_progress_bar

logger = logging.getLogger(__name__)

# ───────────────────────── вспомогательные функции ─────────────────────────
_RX_SPACES = re.compile(r"\s+")
_RX_VARIANTS = re.compile(r"[;,/]|(?:\s+или\s+)", re.I)


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
        InlineKeyboardButton("🛑 Закончить", callback_data=f"{prefix}:back"),
        InlineKeyboardButton("⏭️ Следующее", callback_data=f"{prefix}:skip"),
    )
    return kb


# ────────────────────────── состояние сессий ────────────────────────────────
@dataclass
class LearningState:
    questions: List[Dict[str, Any]]
    prefix: str  # dtest | mtest
    current: int = 0
    correct: int = 0
    answered: set[int] = field(default_factory=set)


states: Dict[int, LearningState] = {}

# таблицы именно для «learning»
lpoll2user: Dict[str, int] = {}
lpoll2idx: Dict[str, int] = {}
lnav_msgs: Dict[int, int] = {}

# ────────────────────────── keyboards dynamic ──────────────────────────────
def _number_keyboard(prefix: str, current: int) -> InlineKeyboardMarkup:
    """Клавиатура 1-20 (4×5) и кнопка «Назад»."""
    kb = InlineKeyboardMarkup(row_width=5)
    for n in range(1, 21):
        txt = f"{n}{' ✅' if n == current else ''}"
        kb.insert(InlineKeyboardButton(txt, callback_data=f"{prefix}{n}"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="learning:back"))
    return kb


# ────────────────────────── question builders ──────────────────────────────
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
            logger.warning("Learning: skip word '%s' (no translation)", src)
            continue
        rus = rus.strip()
        opts, _ = generate_quiz_options(rus, all_trans, 4)
        opts = [o.strip() for o in opts]
        if rus not in opts:
            opts[0] = rus
        res.append(
            {
                "word": eng,
                "correct": rus,
                "options": opts,
                "correct_index": opts.index(rus),
                "is_revision": revision_flags.get(eng.lower(), False),
            }
        )
    return res


def build_dict_test(chat: int, user: tuple) -> List[Dict[str, Any]]:
    learned = crud.get_learned_words(chat)
    if not learned:
        return []
    cnt = min(_get_user_val(user, 7, 5), len(learned))
    sample = random.sample(learned, cnt)
    level, chosen_set = user[1], _get_user_val(user, 6, None)
    quiz_data = load_quiz_data(level, chosen_set)
    all_tr = [d["translation"].strip() for d in quiz_data]
    return _make_question_list(
        [w for w, _ in sample],
        {w.lower(): t.strip() for w, t in sample},
        all_tr,
        {extract_english(w).lower(): True for w, _ in sample},
    )


def build_memorize(chat: int, user: tuple) -> List[Dict[str, Any]]:
    level = user[1]
    chosen_set = _get_user_val(user, 6, None) or DEFAULT_SETS.get(level)
    words = _read_set_words(level, chosen_set)
    cnt = min(_get_user_val(user, 8, 5), len(words))
    sample = random.sample(words, cnt)
    quiz_data = load_quiz_data(level, chosen_set)
    translations = {d["word"].lower(): d["translation"].strip() for d in quiz_data}
    all_tr = [d["translation"].strip() for d in quiz_data]
    learned = {extract_english(w[0]).lower() for w in crud.get_learned_words(chat)}
    return _make_question_list(
        sample, translations, all_tr, {w: w in learned for w in translations}
    )


# ────────────────────────── helpers (send / finish) ────────────────────────
async def _delete_nav(bot: Bot, chat: int):
    mid = lnav_msgs.pop(chat, None)
    if mid:
        try:
            await bot.delete_message(chat, mid)
        except Exception:
            pass


async def _send_question(chat: int, bot: Bot):
    st = states.get(chat)
    if not st:
        return
    if st.current >= len(st.questions):
        return await _finish(chat, bot)

    q = st.questions[st.current]
    poll = await bot.send_poll(
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
    logger.debug("Learning: poll sent pid=%s chat=%s idx=%d", pid, chat, st.current)

    await _delete_nav(bot, chat)
    bar = format_progress_bar(st.current + 1, len(st.questions), 10)
    msg = await bot.send_message(
        chat,
        f"📊 Прогресс: {st.current + 1}/{len(st.questions)}\n{bar}",
        reply_markup=_make_nav(st.prefix),
        parse_mode="HTML",
    )
    lnav_msgs[chat] = msg.message_id


async def _finish(chat: int, bot: Bot):
    st = states.pop(chat, None)
    if not st:
        return
    await _delete_nav(bot, chat)
    total = len(st.questions)
    perc = st.correct / total * 100 if total else 0
    bar = format_progress_bar(st.correct, total, 20)
    title = "📚 Тест по словарю завершён!" if st.prefix == "dtest" else "📝 Заучивание сета завершено!"
    txt = f"{title}\n\n*Счёт:* {st.correct}/{total} ({perc:.1f} %)\n{bar}"
    if perc < 70:
        txt += "\n\n💡 Повторяйте слова чаще."
    await bot.send_message(chat, txt, parse_mode="Markdown")
    
    # Удаляем отправку стикера
    # if perc >= 70:
    #     await send_sticker_with_menu(chat, bot, get_congratulation_sticker())
    # else:
    await bot.send_message(chat, "Тест завершён.", reply_markup=main_menu_keyboard())
# ────────────────────────── poll-answer handler ────────────────────────────
async def poll_answer_handler(ans: PollAnswer):
    pid = str(ans.poll_id)
    chat = lpoll2user.get(pid)
    qidx = lpoll2idx.get(pid)
    logger.debug("Learning: poll_answer pid=%s chat=%s in_table=%s", pid, chat, pid in lpoll2user)
    if chat is None or qidx is None or chat not in states:
        return  # not ours
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
    logger.debug("Learning: answer chat=%s idx=%d chosen=%s ok=%s", chat, qidx, chosen_txt, ok)

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


# ────────────────────────── settings handlers ──────────────────────────────
async def _update_user_setting(chat: int, field: str, value: int):
    """Обновляем поле в БД (7 – test_words, 8 – memorize_words)."""
    try:
        if field == "test":
            crud.set_test_words(chat, value)
        else:
            crud.set_memorize_words(chat, value)
        logger.info("Learning: update %s_words → %d (chat=%s)", field, value, chat)
    except AttributeError:
        idx = 7 if field == "test" else 8
        crud.update_user_field(chat, idx, value)
        logger.info("Learning: fallback update field idx=%d value=%d", idx, value)
    except Exception as e:
        logger.error("Learning: cannot update setting (%s_words=%d) – %s", field, value, e)
        raise


async def handle_learning_settings(cb: types.CallbackQuery, bot: Bot):
    chat = cb.from_user.id
    data = cb.data
    user = crud.get_user(chat)
    if not user:
        return await cb.answer("Профиль не найден", show_alert=True)

    # --- Кнопка «Назад» из подменю настроек
    if data == "learning:back":
        return await cb.message.edit_text(
            "📚 Выберите режим обучения:", reply_markup=learning_menu_keyboard()
        )

    # --- открываем подменю «Настройки обучения»
    if data == "learning:settings":
        return await cb.message.edit_text(
            "⚙️ Настройки обучения:", reply_markup=learning_settings_keyboard()
        )

    # --- открываем выбор чисел
    if data == "learning:test_settings":
        cur = _get_user_val(user, 7, 5)
        kb = _number_keyboard("set_test_words:", cur)
        return await cb.message.edit_text("🔢 Сколько слов задать в тесте?", reply_markup=kb)

    if data == "learning:memorize_settings":
        cur = _get_user_val(user, 8, 5)
        kb = _number_keyboard("set_memorize_words:", cur)
        return await cb.message.edit_text("🔢 Сколько слов задать в заучивании?", reply_markup=kb)

    # --- выбор конкретного числа
    if data.startswith("set_test_words:"):
        val = int(data.split(":")[1])
        await _update_user_setting(chat, "test", val)
        await cb.answer(f"Сохранено: {val} слов в тесте")
        # Вернуться в меню настроек
        return await handle_learning_settings(cb, bot)

    if data.startswith("set_memorize_words:"):
        val = int(data.split(":")[1])
        await _update_user_setting(chat, "mem", val)
        await cb.answer(f"Сохранено: {val} слов в заучивании")
        return await handle_learning_settings(cb, bot)

    # неизвестный коллбек – не страшно
    logger.warning("Learning settings: unhandled %s", data)
    await cb.answer()


# ────────────────────────── start learning modes ───────────────────────────
async def _start(cb: types.CallbackQuery, bot: Bot, builder):
    chat = cb.from_user.id
    user = crud.get_user(chat)
    if not user:
        return await cb.answer("Профиль не найден.", show_alert=True)
    qs = builder(chat, user)
    if not qs:
        return await cb.answer("Нет данных для теста.", show_alert=True)
    prefix = "dtest" if builder is build_dict_test else "mtest"
    states[chat] = LearningState(qs, prefix)
    logger.debug("Learning: new session chat=%s prefix=%s qs=%d", chat, prefix, len(qs))
    await cb.answer()
    await _send_question(chat, bot)


# ────────────────────────── registration ───────────────────────────────────
def register_learning_handlers(dp: Dispatcher, bot: Bot | None = None):
    # ответы на Quiz-poll
    dp.register_poll_answer_handler(
        poll_answer_handler, lambda a: str(a.poll_id) in lpoll2user
    )

    # запуск режимов
    dp.register_callback_query_handler(
        lambda c: asyncio.create_task(_start(c, bot, build_dict_test)),
        lambda c: c.data == "learning:dictionary_test",
    )
    dp.register_callback_query_handler(
        lambda c: asyncio.create_task(_start(c, bot, build_memorize)),
        lambda c: c.data == "learning:memorize_set",
    )

    # навигация «следующее / закончить» внутри сессии
    dp.register_callback_query_handler(
        lambda c: asyncio.create_task(nav_callback(c, bot)),
        lambda c: c.data.startswith(("dtest:", "mtest:")),
    )

    # открыть главное меню «Обучение»
    dp.register_callback_query_handler(
        lambda c: c.message.edit_text(
            "📚 Выберите режим обучения:", reply_markup=learning_menu_keyboard()
        ),
        lambda c: c.data == "menu:learning",
    )

    # настройки обучения (включая «Назад»)
    dp.register_callback_query_handler(
        lambda c: asyncio.create_task(handle_learning_settings(c, bot)),
        lambda c: c.data.startswith(
            (
                "learning:settings",
                "learning:test_settings",
                "learning:memorize_settings",
                "set_test_words:",
                "set_memorize_words:",
                "learning:back",
            )
        ),
    )

    # fallback для логирования нематченных callback из обучающих меню
    async def _unhandled(cb: types.CallbackQuery):
        logger.warning("Learning: UNHANDLED callback %s", cb.data)
        await cb.answer()

    dp.register_callback_query_handler(_unhandled, lambda c: c.data.startswith("learning:"))


# ────────────────────────── nav callback (skip/back) ───────────────────────
async def nav_callback(cb: types.CallbackQuery, bot: Bot):
    chat = cb.from_user.id
    prefix, action = cb.data.split(":", 1)
    st = states.get(chat)
    if not st or st.prefix != prefix:
        return await cb.answer()

    if action == "skip":
        # пропустить вопрос
        st.current += 1
        await cb.answer("Вопрос пропущен")
        await _send_question(chat, bot)
    elif action == "back":
        # досрочно завершить
        await cb.answer("Сессия завершена")
        await _finish(chat, bot)
