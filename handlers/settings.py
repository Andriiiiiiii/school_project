# handlers/settings.py
from __future__ import annotations

import logging
from functools import partial
from pathlib import Path
from zoneinfo import ZoneInfo
import urllib.parse

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.exceptions import MessageNotModified

from config import LEVELS_DIR, REMINDER_START, DURATION_HOURS, DEFAULT_SETS
from database import crud
from keyboards.main_menu import main_menu_keyboard
from keyboards.submenus import (
    level_selection_keyboard,
    notification_settings_menu_keyboard,
    settings_menu_keyboard,
)
from utils.helpers import (
    extract_english,
    get_daily_words_for_user,
    reset_daily_words_cache,
)
from utils.sticker_helper import get_congratulation_sticker, send_sticker_with_menu
from utils.visual_helpers import format_progress_bar

# ──────────────────────────────── ЛОГИ + КЭШ ───────────────────────────────
logger = logging.getLogger(__name__)

pending_settings: dict[int, str] = {}       # chat_id → "words"/"repetitions"
user_set_selection: dict[int, str] = {}     # chat_id → set_name
set_index_cache: dict[str, str] = {}        # f"{chat_id}_{idx}" → set_name

# ──────────────────────────────── КОНСТАНТЫ ────────────────────────────────
WORDS_RANGE = range(1, 21)
REPS_RANGE = range(1, 6)
MAX_TG_MSG = 3800
ENCODINGS = ("utf-8", "cp1251")

timezones_map = {
    2: "Калининград", 3: "Москва", 4: "Самара", 5: "Екатеринбург", 6: "Омск",
    7: "Красноярск",  8: "Иркутск", 9: "Якутск", 10: "Владивосток",
    11: "Магадан",    12: "Камчатка",
}
russian_tzs = {
    2: "Europe/Kaliningrad",  3: "Europe/Moscow",       4: "Europe/Samara",
    5: "Asia/Yekaterinburg",  6: "Asia/Omsk",           7: "Asia/Krasnoyarsk",
    8: "Asia/Irkutsk",        9: "Asia/Yakutsk",        10: "Asia/Vladivostok",
    11: "Asia/Magadan",       12: "Asia/Kamchatka",
}

# ──────────────────────────────── ВСПОМОГАТЕЛЬНЫЕ ──────────────────────────
def _read_file(path: Path) -> str:
    """Безопасное чтение текста (UTF-8 / CP1251)."""
    for enc in ENCODINGS:
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    raise IOError(f"Не удалось прочитать {path}")

def _first_n_words(path: Path, n: int = 30) -> str:
    """Первые *n* строк файла, лишние пробелы удалены."""
    try:
        text = _read_file(path)
    except IOError:
        logger.warning("Не удалось показать превью сета %s", path)
        return "Ошибка чтения файла."
    words = [ln.strip() for ln in text.splitlines() if ln.strip()][:n]
    preview = "\n".join(words)
    if len(words) == n:
        preview += "\n…"
    return preview or "Файл пуст."

def _shorten(intro: str, body: str, max_length: int = 3800) -> str:
    """Обрезает `body`, чтобы сообщение < 4096 симв."""
    # Проверяем общую длину
    total_length = len(intro) + len(body)
    
    if total_length <= max_length:
        return intro + body
        
    # Вычисляем доступное место для body
    available_for_body = max_length - len(intro) - 100  # запас для сообщения об обрезке
    
    if available_for_body <= 0:
        # Если даже intro слишком длинное
        return intro[:max_length - 50] + "\n\n⚠️ *Сообщение обрезано*"
    
    # Обрезаем body по строкам
    lines = body.splitlines()
    result_lines = []
    current_length = 0
    
    for line in lines:
        if current_length + len(line) + 1 > available_for_body:
            break
        result_lines.append(line)
        current_length += len(line) + 1
    
    # Подсчитываем сколько слов не показано
    shown_count = len(result_lines)
    total_count = len(lines)
    skipped = total_count - shown_count
    
    result = intro + "\n".join(result_lines)
    
    if skipped > 0:
        result += f"\n\n...и ещё {skipped} слов(а)."
        result += "\n\n⚠️ *Примечание:* Показаны не все слова из-за ограничений Telegram."
    
    return result

def _is_valid_tz(name: str) -> bool:
    try:
        ZoneInfo(name)
        return True
    except Exception:
        return False

def _update_and_refresh(
    chat_id: int,
    *,
    words: int | None = None,
    reps: int | None = None,
    tz: str | None = None,
) -> tuple[int, int]:
    """Обновляет параметры пользователя и сбрасывает кэш."""
    if words is not None:
        crud.update_user_words_per_day(chat_id, words)
    if reps is not None:
        crud.update_user_notifications(chat_id, reps)
    if tz is not None:
        crud.update_user_timezone(chat_id, tz)

    reset_daily_words_cache(chat_id)
    user = crud.get_user(chat_id)
    return user[2], user[3]  # words_per_day, repetitions

def _reschedule(chat_id: int):
    """Пересчёт «слов дня» + обновление планировщика (если есть)."""
    user = crud.get_user(chat_id)
    get_daily_words_for_user(
        chat_id,
        user[1],
        user[2],
        user[3],
        first_time=REMINDER_START,
        duration_hours=DURATION_HOURS,
        force_reset=True,
    )
    try:
        from services.scheduler import reset_user_cache
        reset_user_cache(chat_id)
    except Exception:
        pass

def _numeric_keyboard(prefix: str, rng: range, back_cb: str, current: int = None) -> InlineKeyboardMarkup:
    """Создает клавиатуру с числами, отмечая текущий выбор галочкой."""
    kb = InlineKeyboardMarkup(row_width=5)
    for n in rng:
        # Добавляем зеленую галочку к текущему выбранному значению
        txt = f"{n}{' ✅' if n == current else ''}"
        kb.insert(InlineKeyboardButton(txt, callback_data=f"{prefix}:{n}"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data=back_cb))
    return kb
# ───────────────────────── ОБРАБОТКА ЧИСЛОВОГО ВВОДА ───────────────────────
async def process_settings_input(message: types.Message, bot: Bot):
    chat_id, txt = message.chat.id, message.text.strip()
    if chat_id not in pending_settings:
        return False

    if not txt.isdigit():
        await message.answer(
            "⚠️ Введите число.", reply_markup=notification_settings_menu_keyboard()
        )
        return True

    field = pending_settings.pop(chat_id)  # "words" | "repetitions"
    value = int(txt)
    rng = WORDS_RANGE if field == "words" else REPS_RANGE
    if value not in rng:
        await message.answer(
            "⚠️ Число вне диапазона.", reply_markup=notification_settings_menu_keyboard()
        )
        return True

    words, reps = _update_and_refresh(
        chat_id,
        words=value if field == "words" else None,
        reps=value if field == "repetitions" else None,
    )
    _reschedule(chat_id)
    await message.answer(
        f"✅ Настройки обновлены!\n\n📊 Слов/день: *{words}*\n🔄 Повторений: *{reps}*",
        parse_mode="Markdown",
        reply_markup=notification_settings_menu_keyboard(),
    )
    return True

# ───────────────────────────── МЕНЮ НАСТРОЕК ───────────────────────────────
async def show_settings_callback(cb: types.CallbackQuery, bot: Bot):
    await cb.message.edit_text(
        "🏠 Персонализация:\n\nВыберите раздел для настройки:",
        reply_markup=settings_menu_keyboard()
    )
    await cb.answer()

async def process_settings_choice_callback(cb: types.CallbackQuery, bot: Bot):
    _, option = cb.data.split(":", 1)
    chat_id = cb.from_user.id
    user = crud.get_user(chat_id)

    if option == "level":
        await cb.message.edit_text(
            "🔤 *Выберите уровень сложности:*",
            parse_mode="Markdown",
            reply_markup=level_selection_keyboard(),
        )

    elif option == "notifications":
        await cb.message.edit_text(
            "⚙️ *Настройки уведомлений*",
            parse_mode="Markdown",
            reply_markup=notification_settings_menu_keyboard(),
        )


    elif option == "words":
        current_words = user[2]  # Текущее количество слов
        await cb.message.edit_text(
            f"📊 *Количество слов в день*\n\nТекущее: *{current_words}*",
            parse_mode="Markdown",
            reply_markup=_numeric_keyboard("set_words", WORDS_RANGE, "settings:notifications", current=current_words),
        )

    elif option == "repetitions":
        current_reps = user[3]  # Текущее количество повторений
        await cb.message.edit_text(
            f"🔄 *Количество повторений*\n\nТекущее: *{current_reps}*",
            parse_mode="Markdown",
            reply_markup=_numeric_keyboard(
                "set_repetitions", REPS_RANGE, "settings:notifications", current=current_reps
            ),
        )
        
    elif option == "timezone":
        kb = InlineKeyboardMarkup(row_width=3)
        for off in range(2, 13):
            kb.insert(
                InlineKeyboardButton(
                    f"UTC+{off} {timezones_map[off]}",
                    callback_data=f"set_timezone:{off}",
                )
            )
        kb.add(InlineKeyboardButton("🔙 Назад", callback_data="settings:back"))
        await cb.message.edit_text(
            "🌐 *Выберите часовой пояс*", parse_mode="Markdown", reply_markup=kb
        )

    elif option == "set":
        await process_my_sets(cb, bot)

    elif option == "mysettings":
        await process_settings_mysettings(cb, bot)

    await cb.answer()

# ──────────────────────── WORDS / REP BUTTONS ──────────────────────────────
async def handle_set_words_count(cb: types.CallbackQuery, bot: Bot):
    _, num = cb.data.split(":", 1)
    words, reps = _update_and_refresh(cb.from_user.id, words=int(num))
    _reschedule(cb.from_user.id)
    await cb.message.edit_text(
        f"✅ Сохранено!\n\n📊 Слов/день: *{words}*\n🔄 Повторений: *{reps}*",
        parse_mode="Markdown",
        reply_markup=notification_settings_menu_keyboard(),
    )
    await cb.answer()

async def handle_set_repetitions_count(cb: types.CallbackQuery, bot: Bot):
    _, num = cb.data.split(":", 1)
    words, reps = _update_and_refresh(cb.from_user.id, reps=int(num))
    _reschedule(cb.from_user.id)
    await cb.message.edit_text(
        f"✅ Сохранено!\n\n📊 Слов/день: *{words}*\n🔄 Повторений: *{reps}*",
        parse_mode="Markdown",
        reply_markup=notification_settings_menu_keyboard(),
    )
    await cb.answer()

# ───────────────────────────── ЧАСОВОЙ ПОЯС ───────────────────────────────
async def process_set_timezone_callback(cb: types.CallbackQuery, bot: Bot):
    _, off_str = cb.data.split(":", 1)
    off = int(off_str)
    tz = russian_tzs.get(off, f"Etc/GMT-{off}")
    if not _is_valid_tz(tz):
        tz = "Europe/Moscow"

    _update_and_refresh(cb.from_user.id, tz=tz)
    _reschedule(cb.from_user.id)
    await cb.message.edit_text("✅ Часовой пояс обновлён.", reply_markup=settings_menu_keyboard())
    await cb.answer()

# ─────────────────────────────── УРОВЕНЬ ───────────────────────────────────
async def process_set_level_callback(cb: types.CallbackQuery, bot: Bot):
    """Устанавливает новый уровень для пользователя без сброса кэша слов дня."""
    _, level = cb.data.split(":", 1)
    crud.update_user_level(cb.from_user.id, level)
    # Удаляем строку с reset_daily_words_cache, чтобы не сбрасывать кэш
    await cb.message.edit_text(f"🔤 Уровень изменён на {level}.", reply_markup=settings_menu_keyboard())
    await cb.answer()
# ─────────────────────────── МОИ СЕТЫ (СПИСОК) ────────────────────────────

# В файле handlers/settings.py найти функцию process_my_sets и заменить ее на эту:

async def process_my_sets(cb: types.CallbackQuery, bot: Bot):
    chat_id = cb.from_user.id
    user = crud.get_user(chat_id)
    if not user:
        await bot.send_message(chat_id, "Пользователь не найден.")
        return
        
    level = user[1]
    level_dir = Path(LEVELS_DIR) / level
    if not level_dir.exists():
        await bot.send_message(chat_id, f"Папка уровня {level} не найдена.")
        return

    # Импортируем функции для работы с подпиской
    from utils.subscription_helpers import get_available_sets_for_user, is_set_available_for_user
    
    # Получаем все наборы для текущего уровня пользователя
    all_sets = sorted(f.stem for f in level_dir.glob("*.txt"))
    available_sets = get_available_sets_for_user(chat_id, level)
    is_premium = crud.is_user_premium(chat_id)
    
    logger.info(f"User {chat_id} (level {level}, premium: {is_premium}): {len(all_sets)} total sets, {len(available_sets)} available")
    
    if not all_sets:
        await bot.send_message(chat_id, "Сетов не найдено.")
        return

    current = user_set_selection.get(chat_id) or user[6]
    kb = InlineKeyboardMarkup(row_width=1)
    set_index_cache.clear()

    for idx, name in enumerate(all_sets, 1):
        key = f"{chat_id}_{idx}"
        set_index_cache[key] = name
        
        # Подсчитываем количество слов в каждом наборе
        try:
            set_path = level_dir / f"{name}.txt"
            with open(set_path, 'r', encoding='utf-8') as f:
                word_count = len([line for line in f if line.strip()])
            button_text = f"{name} ({word_count} слов)"
        except Exception as e:
            logger.error(f"Ошибка при подсчете слов в {name}: {e}")
            button_text = name
        
        # Проверяем доступность набора
        is_available = name in available_sets  # Используем результат get_available_sets_for_user
        
        if not is_available:
            button_text += " 🔒"  # Заблокированный набор
        elif current and current == name:
            button_text += " ✅"  # Текущий набор
        
        # Определяем callback в зависимости от доступности
        if is_available:
            cb_name = "confirm_idx" if current and current != name else "set_idx"
            kb.add(InlineKeyboardButton(button_text, callback_data=f"{cb_name}:{idx}"))
        else:
            # Для заблокированных наборов - переход к подписке
            kb.add(InlineKeyboardButton(button_text, callback_data="subscription:info"))

    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="menu:settings"))
    
    # Формируем текст сообщения
    text = f"📚 *Наборы слов для уровня {level}*\n\n"
    if current:
        # Проверяем доступность текущего набора
        current_available = current in available_sets
        if current_available:
            text += f"Текущий набор: *{current}*\n\n"
        else:
            text += f"Текущий набор: *{current}* 🔒 (требует Premium)\n\n"
    
    if not is_premium:
        locked_count = len(all_sets) - len(available_sets)
        text += f"🆓 Доступно: {len(available_sets)} из {len(all_sets)} наборов\n"
        if locked_count > 0:
            text += f"🔒 Заблокировано: {locked_count} наборов\n\n"
            text += "Получите Premium для доступа ко всем наборам!\n\n"
    else:
        text += "💎 Premium: доступны все наборы\n\n"
    
    text += "Выберите набор для изучения:"
    
    await bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=kb)

# ────────────────────────── ВЫБОР / СМЕНА СЕТА ────────────────────────────
async def handle_set_by_index(cb: types.CallbackQuery, bot: Bot):
    _, idx = cb.data.split(":", 1)
    await _choose_set(cb, int(idx), confirm=False)

async def handle_confirm_set_by_index(cb: types.CallbackQuery, bot: Bot):
    _, idx = cb.data.split(":", 1)
    await _choose_set(cb, int(idx), confirm=True)

async def _choose_set(cb: types.CallbackQuery, idx: int, *, confirm: bool):
    key = f"{cb.from_user.id}_{idx}"
    set_name = set_index_cache.get(key)
    if not set_name:
        await cb.answer("Ошибка. Попробуйте заново.")
        return

    # ИСПРАВЛЕНИЕ: Проверяем, является ли выбранный набор уже текущим
    chat_id = cb.from_user.id
    user = crud.get_user(chat_id)
    current_set = user_set_selection.get(chat_id) or user[6]
    
    if current_set == set_name:
        # Набор уже выбран, показываем его содержимое без смены
        await _show_current_set_content(cb, set_name, user[1])
        return

    if confirm:
        # показываем первые 30 слов для превью
        level = user[1]
        preview_path = Path(LEVELS_DIR) / level / f"{set_name}.txt"
        preview_text = _first_n_words(preview_path)
        
        # Подсчитываем общее количество слов
        total_words = 50  # значение по умолчанию
        try:
            with open(preview_path, 'r', encoding='utf-8') as f:
                total_words = len([line for line in f if line.strip()])
        except Exception as e:
            logger.error(f"Ошибка при подсчете слов: {e}")

        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("✅ Да", callback_data=f"set_chg_idx:{idx}"),
            InlineKeyboardButton("❌ Нет", callback_data="set_change_cancel"),
        )
        await cb.message.edit_text(
            f"⚠️ *Внимание!* Смена набора сбросит весь ваш прогресс.\n\n"
            f"Новый набор: *«{set_name}»*\n"
            f"Всего слов в наборе: *{total_words}*\n\n"
            f"Первые 30 слов:\n{preview_text}\n\n"
            f"Вы уверены, что хотите сменить набор?",
            parse_mode="Markdown",
            reply_markup=kb,
        )
    else:
        await handle_set_change_confirmed_by_index(cb, cb.bot, idx_override=idx)

async def _show_current_set_content(cb: types.CallbackQuery, set_name: str, level: str):
    """Показывает содержимое уже выбранного набора без смены."""
    try:
        set_path = Path(LEVELS_DIR) / level / f"{set_name}.txt"
        content = _read_file(set_path)
        
        # Подсчитываем количество слов
        word_count = len([line for line in content.splitlines() if line.strip()])

        intro = (
            f"📚 *Набор «{set_name}» уже выбран*\n\n"
            f"🔤 Уровень: *{level}*\n"
            f"📊 Всего слов в наборе: *{word_count}*\n\n"
            f"Полный список слов из набора:\n\n"
        )
        
        await cb.message.edit_text(
            _shorten(intro, content), 
            parse_mode="Markdown", 
            reply_markup=settings_menu_keyboard()
        )
        await cb.answer("Этот набор уже выбран")
        
    except Exception as e:
        logger.error(f"Ошибка при показе содержимого набора: {e}")
        await cb.message.edit_text(
            f"📚 *Набор «{set_name}» уже выбран*\n\nНе удалось загрузить содержимое набора.",
            parse_mode="Markdown", 
            reply_markup=settings_menu_keyboard()
        )
        await cb.answer("Этот набор уже выбран")

async def handle_set_change_confirmed_by_index(
    cb: types.CallbackQuery,
    bot: Bot,
    *,
    idx_override: int | None = None,
):
    idx = idx_override or int(cb.data.split(":", 1)[1])
    key = f"{cb.from_user.id}_{idx}"
    set_name = set_index_cache.get(key)
    if not set_name:
        await cb.answer("Ошибка.")
        return

    chat_id = cb.from_user.id
    crud.clear_learned_words_for_user(chat_id)
    crud.update_user_chosen_set(chat_id, set_name)
    user_set_selection[chat_id] = set_name
    reset_daily_words_cache(chat_id)

    level = crud.get_user(chat_id)[1]
    set_path = Path(LEVELS_DIR) / level / f"{set_name}.txt"
    content = _read_file(set_path)
    
    # Подсчитываем количество слов
    word_count = len([line for line in content.splitlines() if line.strip()])

    intro = (
        f"✅ *Набор успешно изменен!*\n\n"
        f"📚 Выбран набор: *«{set_name}»*\n"
        f"🔤 Уровень: *{level}*\n"
        f"📊 Всего слов в наборе: *{word_count}*\n"
        f"⚠️ Ваш словарь был очищен.\n\n"
        f"Полный список слов из набора:\n\n"
    )
    
    await cb.message.edit_text(
        _shorten(intro, content), 
        parse_mode="Markdown", 
        reply_markup=settings_menu_keyboard()
    )
    await cb.answer()

async def handle_set_change_cancelled(cb: types.CallbackQuery, bot: Bot):
    """Отменяет смену набора и возвращает в главное меню."""
    from keyboards.main_menu import main_menu_keyboard
    
    await cb.message.edit_text(
        "📋 Главное меню:",
        reply_markup=main_menu_keyboard()
    )
    await cb.answer("Смена набора отменена")

# ───────────────────────── МОИ НАСТРОЙКИ (ПРОФИЛЬ) ────────────────────────
async def process_settings_mysettings(cb: types.CallbackQuery, bot: Bot):
    chat_id = cb.from_user.id
    user = crud.get_user(chat_id)
    if not user:
        try:
            await cb.message.edit_text("Профиль не найден.", reply_markup=main_menu_keyboard())
        except Exception:
            await bot.send_message(chat_id, "Профиль не найден.", reply_markup=main_menu_keyboard())
        return

    level, words, reps, tz = user[1], user[2], user[3], user[5] or "не задан"
    chosen = user_set_selection.get(chat_id) or user[6] or "не выбран"

    # Получаем информацию о днях подряд
    try:
        from database.crud import get_user_streak
        streak, last_test_date = get_user_streak(chat_id)
    except Exception:
        streak = 0
        
    text = (
        "👤 *Ваш профиль*\n\n"
        f"🔤 *Уровень:* {level}\n"
        f"📊 *Слов/день:* {words}\n"
        f"🔄 *Повторений:* {reps}\n"
        f"🌐 *Часовой пояс:* {tz}\n"
        f"🔥 *Дней подряд:* {streak}\n"
    )

    # Добавляем информацию о наборе с количеством слов
    if chosen != "не выбран":
        set_path = Path(LEVELS_DIR) / level / f"{chosen}.txt"
        if set_path.exists():
            try:
                set_words = [
                    extract_english(w).lower()
                    for w in _read_file(set_path).splitlines()
                    if w.strip()
                ]
                total_words = len(set_words)
                learnt_en = {extract_english(w[0]).lower() for w in crud.get_learned_words(chat_id)}
                done = sum(1 for w in set_words if w in learnt_en)
                
                text += f"📚 *Набор:* {chosen} ({total_words} слов)\n"
                
                bar = format_progress_bar(done, total_words, 10)
                text += f"\n📈 Прогресс:\n{bar}\n"
                
                # Добавляем информацию о том, сколько осталось выучить
                remaining = total_words - done
                if remaining > 0:
                    days_to_complete = (remaining + words - 1) // words  # округление вверх
                    text += f"\n⏳ *Осталось выучить:* {remaining} слов (~{days_to_complete} дней)"
                else:
                    text += f"\n🎉 *Поздравляем!* Вы выучили весь набор!"
            except Exception as e:
                logger.error(f"Ошибка при чтении набора: {e}")
                text += f"📚 *Набор:* {chosen}\n"
        else:
            text += f"📚 *Набор:* {chosen} (файл не найден)\n"
    else:
        text += f"📚 *Набор:* не выбран\n"

    try:
        await cb.message.edit_text(text, parse_mode="Markdown", reply_markup=settings_menu_keyboard())
    except MessageNotModified:
        # Игнорируем ошибку, если сообщение не изменилось
        logger.debug(f"Settings message not modified for user {chat_id}")
        pass
    except Exception as e:
        logger.error(f"Error editing settings message for user {chat_id}: {e}")
        # Fallback - отправляем новое сообщение
        try:
            await bot.send_message(
                chat_id,
                text,
                parse_mode="Markdown",
                reply_markup=settings_menu_keyboard()
            )
        except Exception as send_error:
            logger.error(f"Failed to send fallback settings message: {send_error}")
    
    await cb.answer()
# ──────────────────────────── BACK-HANDLER ────────────────────────────────
async def _settings_back(cb: types.CallbackQuery, bot: Bot):
    await cb.message.edit_text("Настройки бота:", reply_markup=settings_menu_keyboard())
    await cb.answer()

# ──────────────────────────── РЕГИСТРАЦИЯ ─────────────────────────────────
def register_settings_handlers(dp: Dispatcher, bot: Bot):
    # текстовый ввод
    dp.register_message_handler(
        partial(process_settings_input, bot=bot),
        lambda m: m.chat.id in pending_settings,
        state="*",
        content_types=["text"],
    )

    # главное меню
    dp.register_callback_query_handler(
        partial(show_settings_callback, bot=bot), lambda c: c.data == "menu:settings"
    )
    dp.register_callback_query_handler(
        partial(_settings_back, bot=bot),
        lambda c: c.data in ("settings:back", "notifications:back"),
    )
    dp.register_callback_query_handler(
        partial(process_settings_choice_callback, bot=bot),
        lambda c: c.data and c.data.startswith("settings:") and c.data != "settings:back",
    )

    # words / repetitions
    dp.register_callback_query_handler(
        partial(handle_set_words_count, bot=bot), lambda c: c.data.startswith("set_words:")
    )
    dp.register_callback_query_handler(
        partial(handle_set_repetitions_count, bot=bot),
        lambda c: c.data.startswith("set_repetitions:"),
    )

    # уровень / часовой пояс
    dp.register_callback_query_handler(
        partial(process_set_level_callback, bot=bot), lambda c: c.data.startswith("set_level:")
    )
    dp.register_callback_query_handler(
        partial(process_set_timezone_callback, bot=bot),
        lambda c: c.data.startswith("set_timezone:"),
    )

    # сеты
    dp.register_callback_query_handler(
        partial(handle_set_by_index, bot=bot), lambda c: c.data.startswith("set_idx:")
    )
    dp.register_callback_query_handler(
        partial(handle_confirm_set_by_index, bot=bot),
        lambda c: c.data.startswith("confirm_idx:"),
    )
    dp.register_callback_query_handler(
        partial(handle_set_change_confirmed_by_index, bot=bot),
        lambda c: c.data.startswith("set_chg_idx:"),
    )
    dp.register_callback_query_handler(
        partial(handle_set_change_cancelled, bot=bot), lambda c: c.data == "set_change_cancel"
    )