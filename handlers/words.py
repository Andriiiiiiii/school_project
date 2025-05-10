# handlers/words.py
from __future__ import annotations

import logging
from functools import partial
from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import DURATION_HOURS, LEVELS_DIR, REMINDER_START
from database import crud
from keyboards.submenus import words_day_keyboard
from utils.helpers import (
    get_daily_words_for_user,
    get_user_settings,
    reset_daily_words_cache,
)
from utils.sticker_helper import get_clean_sticker
from utils.visual_helpers import format_daily_words_message

logger = logging.getLogger(__name__)

# ──────────────────────────────── ВСПОМОГАТЕЛЬНЫЕ ──────────────────────────
def _level_dir(level: str) -> Path:
    """Папка уровня."""
    return Path(LEVELS_DIR) / level


def _confirm_keyboard(default_set: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Да, сменить", callback_data=f"confirm_set_change:{default_set}"),
        InlineKeyboardButton("❌ Нет, отмена", callback_data="menu:back"),
    )
    return kb


async def _send_daily_words(
    cb: types.CallbackQuery,
    chat_id: int,
    level: str,
    words_per_day: int,
    reps_per_word: int,
) -> None:
    """Отправка «Слов дня» (или сообщение-ошибку)."""
    result = get_daily_words_for_user(
        chat_id,
        level,
        words_per_day,
        reps_per_word,
        first_time=REMINDER_START,
        duration_hours=DURATION_HOURS,
    )

    # ——— нет слов (нет файла/уровня) ————————————————————————————————
    if result is None:
        await cb.message.edit_text(f"⚠️ Нет слов для уровня {level}.", parse_mode="Markdown")
        await cb.answer()
        return

    # ——— требуется подтверждение смены сета ————————————————
    if len(result) == 3 and result[:2] == (None, None):
        default_set: str = result[2]
        current_set = crud.get_user(chat_id)[6] or "не выбран"
        text = (
            "⚠️ *Внимание! Смена сета сбросит прогресс.*\n\n"
            f"Текущий сет: *{current_set}*\n"
            f"Текущий уровень: *{level}*\n\n"
            f"Сет не соответствует уровню.\n"
            f"Сменить на базовый *{default_set}*?\n"
        )
        await cb.message.edit_text(text, parse_mode="Markdown", reply_markup=_confirm_keyboard(default_set))
        await cb.answer()
        return

    # ——— обычный вывод слов ————————————————————————————————
    messages, times = result
    await cb.message.edit_text(
        format_daily_words_message(messages, times),
        parse_mode="Markdown",
        reply_markup=words_day_keyboard(),
    )
    await cb.answer()


# ─────────────────────────── «СЛОВА ДНЯ» КНОПКА ────────────────────────────
async def send_words_day_schedule(cb: types.CallbackQuery, bot: Bot) -> None:
    chat_id = cb.from_user.id
    user = crud.get_user(chat_id)
    if not user:
        await cb.message.edit_text("⚠️ Профиль не найден. Используйте /start.", parse_mode="Markdown")
        await cb.answer()
        return

    words, reps = get_user_settings(chat_id)
    await _send_daily_words(cb, chat_id, user[1], words, reps)


# ─────────────────────── ПОДТВЕРЖДЕНИЕ СМЕНЫ СЕТА ──────────────────────────
async def handle_confirm_set_change(cb: types.CallbackQuery, bot: Bot) -> None:
    chat_id = cb.from_user.id
    _, default_set = cb.data.split(":", 1)
    user = crud.get_user(chat_id)

    if not user:
        await cb.answer("Профиль не найден.", show_alert=True)
        return

    level = user[1]

    try:
        crud.clear_learned_words_for_user(chat_id)
        crud.update_user_chosen_set(chat_id, default_set)

        # синхронизируем кэш выбранных сетов
        from handlers.settings import user_set_selection

        user_set_selection[chat_id] = default_set
        reset_daily_words_cache(chat_id)

        # стикер-информер
        stick = get_clean_sticker()
        if stick:
            await bot.send_sticker(chat_id, stick)

        words, reps = get_user_settings(chat_id)
        await _send_daily_words(cb, chat_id, level, words, reps)

    except Exception as exc:
        logger.exception("Ошибка смены сета: %s", exc)
        await cb.message.edit_text("❌ Ошибка смены сета. Попробуйте позже.", reply_markup=words_day_keyboard())
        await cb.answer()


# ──────────────────────────── РЕГИСТРАЦИЯ ─────────────────────────────────
def register_words_handlers(dp: Dispatcher, bot: Bot) -> None:
    dp.register_callback_query_handler(
        partial(send_words_day_schedule, bot=bot), lambda c: c.data == "menu:words_day"
    )
    dp.register_callback_query_handler(
        partial(handle_confirm_set_change, bot=bot), lambda c: c.data.startswith("confirm_set_change:")
    )
