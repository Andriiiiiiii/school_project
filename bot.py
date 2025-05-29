# bot.py
"""
Главный файл запуска Telegram‑бота (оптимизированная версия для продакшена)
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
    LOG_LEVEL,
    PRODUCTION_MODE
)
from handlers import register_handlers
from services.scheduler import start_scheduler
from utils.helpers import get_daily_words_for_user, daily_words_cache
from database import crud

# ───────────────────────── Настройка логирования для продакшена ─────────────
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Настройка уровня логирования в зависимости от режима
log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    filename=LOG_DIR / "bot.log",
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    filemode='a'
)

# Ограничиваем логи внешних библиотек
for lib_name in ["aiogram", "asyncio", "aiohttp"]:
    logging.getLogger(lib_name).setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

# ───────────────────────── Восстановление состояния ────────────────────────
LAST_RUN_FILE = Path("last_scheduler_run.pickle")
MAX_BACKFILL_HOURS = 2  # Уменьшено для продакшена

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

# Импорт состояния квиза
try:
    from utils.helpers import quiz_reminder_sent
except (ImportError, AttributeError):
    quiz_reminder_sent: dict[int, str] = {}

def _load_last_run() -> datetime | None:
    """Загружает время последнего запуска планировщика."""
    if not LAST_RUN_FILE.exists():
        return None
    try:
        with LAST_RUN_FILE.open("rb") as f:
            return pickle.load(f)
    except Exception as e:
        if not PRODUCTION_MODE:
            logger.error("Не удалось прочитать файл последнего запуска: %s", e)
        return None

def _save_last_run(ts: datetime) -> None:
    """Сохраняет время последнего запуска планировщика."""
    try:
        with LAST_RUN_FILE.open("wb") as f:
            pickle.dump(ts, f)
    except Exception as e:
        if not PRODUCTION_MODE:
            logger.error("Не удалось сохранить время запуска: %s", e)

async def _recover_missed_notifications() -> None:
    """Восстанавливает пропущенные уведомления (только для критических случаев)."""
    if PRODUCTION_MODE:
        # В продакшене восстанавливаем только за последний час
        max_hours = 1
    else:
        max_hours = MAX_BACKFILL_HOURS
    
    logger.info("Проверка пропущенных уведомлений за последние %d часов", max_hours)
    
    now_srv = datetime.now(tz=ZoneInfo(SERVER_TIMEZONE))
    last_run = _load_last_run() or now_srv - timedelta(hours=max_hours)
    
    if now_srv - last_run > timedelta(hours=max_hours):
        last_run = now_srv - timedelta(hours=max_hours)

    recovered = 0
    try:
        users = crud.get_all_users()
        for user in users[:50]:  # Ограничиваем количество для быстрого старта
            chat_id, level, words_count, reps_count = user[0], user[1], user[2], user[3]
            tz_name = user[5] if len(user) > 5 and user[5] else SERVER_TIMEZONE
            
            try:
                tz = ZoneInfo(tz_name)
                now_loc = now_srv.astimezone(tz)
                last_loc = last_run.astimezone(tz)
                today = now_loc.strftime("%Y-%m-%d")

                result = get_daily_words_for_user(
                    chat_id, level, words_count, reps_count,
                    first_time=REMINDER_START, duration_hours=DURATION_HOURS
                )
                
                if result:
                    msgs, times = result
                    missed = []
                    for t_str, msg in zip(times, msgs):
                        t_dt = datetime.strptime(f"{today} {t_str}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
                        if last_loc < t_dt < now_loc:
                            missed.append((t_str, msg))

                    if missed:
                        # Отправляем только последние 2 пропущенных уведомления
                        text = "⚠️ Пропущенные уведомления:\n\n" + "\n".join(
                            f"📌 {t}: {m}" for t, m in missed[-2:]
                        )
                        await bot.send_message(chat_id, text)
                        recovered += len(missed)

            except Exception as e:
                if not PRODUCTION_MODE:
                    logger.error("Ошибка восстановления для пользователя %s: %s", chat_id, e)

    except Exception as e:
        logger.error("Ошибка при восстановлении уведомлений: %s", e)
    
    if recovered > 0:
        logger.info("Восстановлено %d уведомлений", recovered)
    
    _save_last_run(now_srv)

# ───────────────────────── Fallback для необработанных callback ─────────────
async def _log_unhandled_callback(cb: types.CallbackQuery):
    """Логирует необработанные callback запросы."""
    if not PRODUCTION_MODE:
        logger.warning("Необработанный callback: %s", cb.data)
    await cb.answer()

# ───────────────────────── Инициализация ─────────────────────────────────────
async def on_startup(dispatcher: Dispatcher):
    """Инициализация бота при запуске."""
    # Создаем директорию для уровней
    Path(LEVELS_DIR).mkdir(exist_ok=True)
    
    # Запускаем планировщик
    start_scheduler(bot, asyncio.get_running_loop())
    
    # Устанавливаем команды бота
    from handlers.commands import set_commands
    await set_commands(bot)
    
    # Восстанавливаем пропущенные уведомления
    await _recover_missed_notifications()
    
    logger.info("Бот успешно запущен в режиме: %s", "PRODUCTION" if PRODUCTION_MODE else "DEVELOPMENT")

# ───────────────────────── Регистрация хендлеров ─────────────────────────────
register_handlers(dp, bot)

# Fallback хендлер для неопознанных callback (только в режиме разработки)
if not PRODUCTION_MODE:
    dp.register_callback_query_handler(_log_unhandled_callback, lambda _: True)

# ───────────────────────── Запуск бота ─────────────────────────────────────
if __name__ == "__main__":
    # Настройки для продакшена
    skip_updates = PRODUCTION_MODE  # В продакшене пропускаем старые обновления
    
    executor.start_polling(
        dp, 
        on_startup=on_startup, 
        skip_updates=skip_updates,
        allowed_updates=types.AllowedUpdates.all()
    )

# Экспорт функции для планировщика
save_last_run_time = _save_last_run