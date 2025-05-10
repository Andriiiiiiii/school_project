# bot.py
"""
Запуск Telegram-бота для English Learning.
Настраивает логи, диспетчер, задачи планировщика и обработку пропущенных уведомлений.
"""

import asyncio
import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, executor, types

from config import (
    BOT_TOKEN,
    SERVER_TIMEZONE,
    REMINDER_START,
    DURATION_HOURS,
    LEVELS_DIR,
)
from handlers import register_handlers
from services.scheduler import start_scheduler
from utils.helpers import get_daily_words_for_user, daily_words_cache
from database import crud

# ───────────────────────────────────────────────────────────────
#   Настройка логирования
# ───────────────────────────────────────────────────────────────
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,  # можно сменить на INFO
    filename=LOG_DIR / "bot.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────
#   Файл для хранения времени последнего запуска восстановления
# ───────────────────────────────────────────────────────────────
LAST_RUN_FILE = Path("last_scheduler_run.pickle")
MAX_BACKFILL_HOURS = 3

# ───────────────────────────────────────────────────────────────
#   Инициализация бота и диспетчера
# ───────────────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

# ───────────────────────────────────────────────────────────────
#   Хранилище для флага напоминания квиза
# ───────────────────────────────────────────────────────────────
try:
    from utils.helpers import quiz_reminder_sent
except (ImportError, AttributeError):
    quiz_reminder_sent: dict[int, str] = {}
    logger.debug("Using local quiz_reminder_sent dict")


def _load_last_run() -> datetime | None:
    if not LAST_RUN_FILE.exists():
        return None
    try:
        with LAST_RUN_FILE.open("rb") as f:
            return pickle.load(f)
    except Exception as e:
        logger.error("Не удалось прочитать %s: %s", LAST_RUN_FILE, e)
        return None


def _save_last_run(ts: datetime) -> None:
    try:
        with LAST_RUN_FILE.open("wb") as f:
            pickle.dump(ts, f)
    except Exception as e:
        logger.error("Не удалось записать %s: %s", LAST_RUN_FILE, e)


async def _recover_missed_notifications() -> None:
    logger.info("Проверка пропущенных уведомлений…")
    now_srv = datetime.now(tz=ZoneInfo(SERVER_TIMEZONE))
    last_run = _load_last_run() or now_srv - timedelta(hours=MAX_BACKFILL_HOURS)
    # Ограничиваем максимальную «добигаемость»
    if now_srv - last_run > timedelta(hours=MAX_BACKFILL_HOURS):
        last_run = now_srv - timedelta(hours=MAX_BACKFILL_HOURS)

    recovered = 0
    for user in crud.get_all_users():
        chat_id, level, words_count, reps_count = user[0], user[1], user[2], user[3]
        tz_name = user[5] if len(user) > 5 and user[5] else SERVER_TIMEZONE
        tz = ZoneInfo(tz_name)

        now_loc = now_srv.astimezone(tz)
        last_loc = last_run.astimezone(tz)
        today = now_loc.strftime("%Y-%m-%d")

        try:
            result = get_daily_words_for_user(
                chat_id, level, words_count, reps_count,
                first_time=REMINDER_START, duration_hours=DURATION_HOURS
            )
            if not result:
                continue

            msgs, times = result
            missed = []
            for t_str, msg in zip(times, msgs):
                t_dt = datetime.strptime(f"{today} {t_str}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
                if last_loc < t_dt < now_loc:
                    missed.append((t_str, msg))

            if missed:
                text = "⚠️ Пропущенные уведомления:\n\n" + "\n".join(
                    f"📌 {t}: {m}" for t, m in missed[-3:]
                )
                await bot.send_message(chat_id, text)
                recovered += len(missed)

            # пропущенное напоминание квиза
            base_dt = datetime.strptime(f"{today} {REMINDER_START}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
            quiz_window = base_dt + timedelta(hours=DURATION_HOURS)
            if last_loc < quiz_window < now_loc and quiz_reminder_sent.get(chat_id) != today:
                reminder = (
                    "⚠️ Пропущенное напоминание: пройдите квиз (повторение)."
                    if (chat_id in daily_words_cache
                        and len(daily_words_cache[chat_id]) > 9
                        and daily_words_cache[chat_id][9])
                    else "⚠️ Пропущенное напоминание: пройдите квиз, чтобы выучить слова."
                )
                await bot.send_message(chat_id, reminder)
                quiz_reminder_sent[chat_id] = today
                recovered += 1

        except Exception as e:
            logger.error("Ошибка восстановления для %s: %s", chat_id, e)

    logger.info("Восстановлено %d уведомлений", recovered)
    _save_last_run(now_srv)


async def on_startup(dispatcher: Dispatcher) -> None:
    # создаём директорию с наборами уровней
    Path(LEVELS_DIR).mkdir(exist_ok=True)

    # запускаем планировщик напоминаний
    start_scheduler(bot, asyncio.get_running_loop())

    # регистрируем команды в меню Telegram
    from handlers.commands import set_commands
    await set_commands(bot)

    # восстанавливаем пропущенные уведомления
    await _recover_missed_notifications()

    logger.info("Бот успешно запущен.")


# ───────────────────────────────────────────────────────────────
#   Основной запуск
# ───────────────────────────────────────────────────────────────
register_handlers(dp, bot)

if __name__ == "__main__":
    executor.start_polling(
        dp,
        on_startup=on_startup,
        skip_updates=True,
        allowed_updates=types.AllowedUpdates.all(),
    )
