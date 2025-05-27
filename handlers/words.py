# handlers/words.py
from __future__ import annotations

import logging
from functools import partial
from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import DURATION_HOURS, LEVELS_DIR, REMINDER_START, DEFAULT_SETS
from database import crud
from keyboards.submenus import words_day_keyboard
from utils.helpers import (
    get_daily_words_for_user,
    get_user_settings,
    reset_daily_words_cache,
    previous_daily_words,  # Добавляем этот импорт
)
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
    # Получаем выбранный сет и проверяем соответствие уровню
    user = crud.get_user(chat_id)
    chosen_set = user[6]  # current set from database
    
    # Проверяем несоответствие уровня и сета
    set_level_mismatch = False
    if chosen_set:
        # Проверка на префикс уровня в имени сета
        for prefix in ["A1", "A2", "B1", "B2", "C1", "C2"]:
            if chosen_set.startswith(prefix) and prefix != level:
                set_level_mismatch = True
                break
        
        # Проверяем существование файла для текущего уровня
        set_file_path = Path(LEVELS_DIR) / level / f"{chosen_set}.txt"
        if not set_file_path.exists():
            set_level_mismatch = True
    
    # Если обнаружено несоответствие, предлагаем сменить сет
    if set_level_mismatch:
        default_set = DEFAULT_SETS.get(level, "")
        text = (
            "⚠️ *Внимание!*\n\n"
            f"Текущий набор: *{chosen_set}*\n"
            f"Текущий уровень: *{level}*\n\n"
            f"Вы выбрали уровень не соответствующий текущему набору.\n"
            f"Сменить набор на базовый *{default_set}* для текущего уровня?\n"
        )
        await cb.message.edit_text(text, parse_mode="Markdown", reply_markup=_confirm_keyboard(default_set))
        await cb.answer()
        return
        
    # Получаем слова дня, если нет несоответствия уровня и сета
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

    # ——— требуется подтверждение смены сета (другой случай) ————————————————
    if len(result) == 3 and result[:2] == (None, None):
        default_set: str = result[2]
        current_set = crud.get_user(chat_id)[6] or "не выбран"
        text = (
            "⚠️ *Внимание! Смена набора сбросит прогресс.*\n\n"
            f"Текущий набор: *{current_set}*\n"
            f"Текущий уровень: *{level}*\n\n"
            f"Набор не соответствует уровню.\n"
            f"Сменить на базовый *{default_set}*?\n"
        )
        await cb.message.edit_text(text, parse_mode="Markdown", reply_markup=_confirm_keyboard(default_set))
        await cb.answer()
        return

    # ——— обычный вывод слов ————————————————————————————————
    messages, times = result
    
    # Подсчитываем количество слов в наборе
    total_words = 50  # значение по умолчанию
    try:
        set_file_path = Path(LEVELS_DIR) / level / f"{chosen_set}.txt"
        if set_file_path.exists():
            with open(set_file_path, 'r', encoding='utf-8') as f:
                total_words = len([line for line in f if line.strip()])
    except Exception as e:
        logger.error(f"Ошибка при подсчете слов в наборе: {e}")
    
    # Импортируем функции форматирования
    from utils.visual_helpers import format_daily_words_message, truncate_daily_words_message
    from utils.helpers import daily_words_cache
    
    # Форматируем сообщение
    formatted_message = format_daily_words_message(messages, times, chosen_set, total_words)
    
    # Проверяем длину и обрезаем при необходимости
    if len(formatted_message) > 4000:
        # Получаем уникальные слова из кэша
        unique_words = []
        if chat_id in daily_words_cache:
            entry = daily_words_cache[chat_id]
            if len(entry) > 8 and entry[8]:
                unique_words = entry[8]
        
        # Если не можем получить уникальные слова из кэша, извлекаем из messages
        if not unique_words:
            unique_words = messages
        
        formatted_message = truncate_daily_words_message(
            formatted_message, unique_words, words_per_day, reps_per_word,
            chosen_set, total_words
        )
    
    await cb.message.edit_text(
        formatted_message,
        parse_mode="Markdown",
        reply_markup=words_day_keyboard(),
    )
    await cb.answer()

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
    """Подтверждение смены сета с полной перезагрузкой слов дня."""
    chat_id = cb.from_user.id
    _, default_set = cb.data.split(":", 1)
    user = crud.get_user(chat_id)

    if not user:
        await cb.answer("Профиль не найден.", show_alert=True)
        return

    level = user[1]

    try:
        # Очищаем словарь и меняем сет
        crud.clear_learned_words_for_user(chat_id)
        crud.update_user_chosen_set(chat_id, default_set)

        # Синхронизируем кэш выбранных сетов
        from handlers.settings import user_set_selection
        user_set_selection[chat_id] = default_set
        
        # Гарантированно сбрасываем все кэши для данного пользователя
        reset_daily_words_cache(chat_id)
        
        # Дополнительно удаляем пользователя из кэша previous_daily_words
        if chat_id in previous_daily_words:
            del previous_daily_words[chat_id]
        
        # Принудительно обновляем слова дня
        words, reps = get_user_settings(chat_id)
        
        # ВАЖНО: Создаем новый запрос для слов дня с force_reset=True
        result = get_daily_words_for_user(
            chat_id,
            level,
            words,
            reps,
            first_time=REMINDER_START,
            duration_hours=DURATION_HOURS,
            force_reset=True  # Гарантируем полное обновление слов
        )
        
        if result is None:
            await cb.message.edit_text(f"⚠️ Нет слов для уровня {level}.", parse_mode="Markdown")
            await cb.answer()
            return
            
        messages, times = result
        
        # Подсчитываем количество слов в новом наборе
        total_words = 50  # значение по умолчанию
        try:
            set_file_path = Path(LEVELS_DIR) / level / f"{default_set}.txt"
            if set_file_path.exists():
                with open(set_file_path, 'r', encoding='utf-8') as f:
                    total_words = len([line for line in f if line.strip()])
        except Exception as e:
            logger.error(f"Ошибка при подсчете слов в наборе: {e}")
        
        # Форматируем сообщение с информацией о новом наборе
        from utils.visual_helpers import truncate_daily_words_message
        formatted_message = format_daily_words_message(messages, times, default_set, total_words)
        
        # Проверяем длину и обрезаем при необходимости
        if len(formatted_message) > 4000:
            # Получаем уникальные слова из кэша
            unique_words = []
            if chat_id in daily_words_cache:
                entry = daily_words_cache[chat_id]
                if len(entry) > 8 and entry[8]:
                    unique_words = entry[8]
            
            # Если не можем получить уникальные слова из кэша, используем messages
            if not unique_words:
                unique_words = messages
            
            formatted_message = truncate_daily_words_message(
                formatted_message, unique_words, words, reps,
                default_set, total_words
            )
        
        await cb.message.edit_text(
            formatted_message,
            parse_mode="Markdown",
            reply_markup=words_day_keyboard(),
        )
        await cb.answer(f"✅ Набор успешно изменен на «{default_set}»!")

    except Exception as exc:
        logger.exception("Ошибка смены сета: %s", exc)
        await cb.message.edit_text("❌ Ошибка смены набора. Попробуйте позже.", reply_markup=words_day_keyboard())
        await cb.answer()
# ──────────────────────────── РЕГИСТРАЦИЯ ─────────────────────────────────
def register_words_handlers(dp: Dispatcher, bot: Bot) -> None:
    dp.register_callback_query_handler(
        partial(send_words_day_schedule, bot=bot), lambda c: c.data == "menu:words_day"
    )
    dp.register_callback_query_handler(
        partial(handle_confirm_set_change, bot=bot), lambda c: c.data.startswith("confirm_set_change:")
    )
