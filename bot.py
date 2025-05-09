# bot.py
import asyncio
import logging
import os
import pickle
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, executor, types

from config import BOT_TOKEN, SERVER_TIMEZONE, REMINDER_START, DURATION_HOURS
from handlers import register_handlers
from services.scheduler import start_scheduler
from utils.helpers import get_daily_words_for_user, daily_words_cache
from database import crud
from config import LEVELS_DIR

# ────────── логирование ────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,                 # при желании смените на INFO
    filename="logs/bot.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
# ────────────────────────────────────────────────────────────────


# ────────── Import / fallback для quiz_reminder_sent ───────────
try:
    from utils.helpers import quiz_reminder_sent  # type: ignore
except (ImportError, AttributeError):
    quiz_reminder_sent: dict[int, str] = {}
    logger.debug("utils.helpers.quiz_reminder_sent not found – using local dict")
# ────────────────────────────────────────────────────────────────


# ────────── константы для missed-notifications ─────────────────
LAST_RUN_FILE = "last_scheduler_run.pickle"
MAX_BACKFILL_HOURS = 3
# ────────────────────────────────────────────────────────────────


# ────────── Bot & Dispatcher ────────────────────────────────────
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)
# ────────────────────────────────────────────────────────────────


# ────────── util-функции сохранения времени ────────────────────
def get_last_run_time() -> datetime | None:
    try:
        if os.path.exists(LAST_RUN_FILE):
            with open(LAST_RUN_FILE, "rb") as f:
                return pickle.load(f)
    except Exception as exc:
        logger.error("Error reading last run file: %s", exc)
    return None


def save_last_run_time(ts: datetime) -> None:
    try:
        with open(LAST_RUN_FILE, "wb") as f:
            pickle.dump(ts, f)
    except Exception as exc:
        logger.error("Error writing last run file: %s", exc)
# ────────────────────────────────────────────────────────────────


# ────────── проверка пропущенных уведомлений ────────────────────
async def check_missed_notifications():
    logger.info("Checking missed notifications…")
    now_srv = datetime.now(tz=ZoneInfo(SERVER_TIMEZONE))
    last_run = get_last_run_time() or now_srv
    if last_run < now_srv - timedelta(hours=MAX_BACKFILL_HOURS):
        last_run = now_srv - timedelta(hours=MAX_BACKFILL_HOURS)

    recovered = 0
    for user in crud.get_all_users():
        try:
            chat_id, level, words, reps = user[0], user[1], user[2], user[3]
            tz = user[5] if len(user) > 5 and user[5] else "Europe/Moscow"

            now_loc = now_srv.astimezone(ZoneInfo(tz))
            last_loc = last_run.astimezone(ZoneInfo(tz))
            today = now_loc.strftime("%Y-%m-%d")

            res = get_daily_words_for_user(chat_id, level, words, reps,
                                           first_time=REMINDER_START,
                                           duration_hours=DURATION_HOURS)
            if not res:
                continue
            msgs, times = res
            missed = []
            for t, msg in zip(times, msgs):
                nt = datetime.strptime(f"{today} {t}",
                                       "%Y-%m-%d %H:%M").replace(tzinfo=now_loc.tzinfo)
                if last_loc < nt < now_loc:
                    missed.append((t, msg))
            if missed:
                txt = "⚠️ Пропущенные уведомления:\n\n" + \
                      "\n".join(f"📌 {t}:\n{m}" for t, m in missed[-3:])
                await bot.send_message(chat_id, txt)
                recovered += len(missed)

            # пропущенный квиз-reminder
            base = datetime.strptime(f"{today} {REMINDER_START}",
                                     "%Y-%m-%d %H:%M").replace(tzinfo=now_loc.tzinfo)
            if last_loc < base + timedelta(hours=DURATION_HOURS) < now_loc \
               and quiz_reminder_sent.get(chat_id) != today:
                txt = ("⚠️ Пропущенное напоминание: пройдите квиз (повторение)."
                       if chat_id in daily_words_cache and
                          len(daily_words_cache[chat_id]) > 9 and
                          daily_words_cache[chat_id][9]
                       else
                       "⚠️ Пропущенное напоминание: пройдите квиз, чтобы выучить слова.")
                await bot.send_message(chat_id, txt)
                quiz_reminder_sent[chat_id] = today
                recovered += 1
        except Exception as exc:
            logger.error("Recovery error for %s: %s", user[0], exc)

    logger.info("Recovered %d missed notifications", recovered)
    save_last_run_time(now_srv)
# ────────────────────────────────────────────────────────────────


# ────────── on_startup ──────────────────────────────────────────
async def on_startup(dp: Dispatcher):
    # создаём каталоги уровней (минимально)
    os.makedirs(LEVELS_DIR, exist_ok=True)

    # запускаем scheduler
    start_scheduler(bot, asyncio.get_running_loop())

    # регистрируем команды
    from handlers.commands import set_commands
    await set_commands(bot)

    # восстанавливаем пропущенные уведомления
    await check_missed_notifications()

    logger.info("Bot started successfully.")
# ────────────────────────────────────────────────────────────────


# ────────── регистрация всех хендлеров ─────────────────────────
register_handlers(dp, bot)
# ────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    executor.start_polling(
        dp,
        on_startup=on_startup,
        skip_updates=True,
        # главное: запрашиваем ВСЕ типы обновлений, включая poll_answer
        allowed_updates=types.AllowedUpdates.all(),
    )
