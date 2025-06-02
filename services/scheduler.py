# services/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import asyncio
import logging
from aiogram import Bot
from zoneinfo import ZoneInfo
from database import crud
from utils.helpers import get_daily_words_for_user, daily_words_cache, previous_daily_words, reset_daily_words_cache
from utils.visual_helpers import extract_english
from config import REMINDER_START, DURATION_HOURS, SERVER_TIMEZONE, PRODUCTION_MODE

logger = logging.getLogger(__name__)
FIRST_TIME = REMINDER_START

# Глобальные переменные
test_reminder_sent = {}
user_cache = {}
last_cache_update = 0
last_payment_check = 0

# Оптимизированные интервалы для продакшена
CACHE_UPDATE_INTERVAL = 1800 if PRODUCTION_MODE else 900  # 30 мин в продакшене, 15 мин в разработке
PAYMENT_CHECK_INTERVAL = 600 if PRODUCTION_MODE else 300  # 10 мин в продакшене, 5 мин в разработке

def scheduler_job(bot: Bot, loop: asyncio.AbstractEventLoop):
    """
    Оптимизированная функция планировщика для продакшена.
    """
    global last_cache_update, user_cache, last_payment_check
    
    try:
        # Получаем серверное время
        try:
            now_server = datetime.now(tz=ZoneInfo(SERVER_TIMEZONE))
        except Exception:
            now_server = datetime.now(tz=ZoneInfo("UTC"))
        
        current_time = now_server.timestamp()
        
        # Проверка платежей (реже в продакшене)
        if current_time - last_payment_check > PAYMENT_CHECK_INTERVAL:
            asyncio.run_coroutine_threadsafe(check_payments_job(bot), loop)
            last_payment_check = current_time
        
        # Обновление кэша пользователей (реже в продакшене)
        if current_time - last_cache_update > CACHE_UPDATE_INTERVAL:
            try:
                user_cache = {user[0]: user for user in crud.get_all_users()}
                last_cache_update = current_time
                logger.info("Кэш пользователей обновлен: %d пользователей", len(user_cache))
            except Exception as e:
                logger.error("Ошибка обновления кэша пользователей: %s", e)
                if not user_cache:
                    try:
                        user_cache = {user[0]: user for user in crud.get_all_users()}
                    except Exception:
                        user_cache = {}
        
        if not user_cache:
            return
        
        # Обработка пользователей
        processed_count = 0
        for chat_id, user in user_cache.items():
            try:
                timezone = user[5] if len(user) > 5 and user[5] else "Europe/Moscow"
                
                try:
                    now_local = now_server.astimezone(ZoneInfo(timezone))
                except Exception:
                    now_local = now_server.astimezone(ZoneInfo("Europe/Moscow"))
                    
                # Проверка на полночь для сброса данных
                local_hour = now_local.hour
                local_minute = now_local.minute
                
                if local_hour == 0 and local_minute <= 3:
                    process_daily_reset(chat_id)
                    processed_count += 1
                    continue
                
                # Проверка необходимости обработки
                now_local_str = now_local.strftime("%H:%M")
                needs_processing = False
                
                # Проверка времени уведомлений
                try:
                    result = get_daily_words_for_user(
                        chat_id, user[1], user[2], user[3],
                        first_time=FIRST_TIME, duration_hours=DURATION_HOURS
                    )
                    if result and now_local_str in result[1]:
                        needs_processing = True
                except Exception as e:
                    if not PRODUCTION_MODE:
                        logger.error("Ошибка проверки уведомлений для пользователя %s: %s", chat_id, e)
                
                # Проверка времени напоминания о тесте
                try:
                    local_today_str = now_local.strftime("%Y-%m-%d")
                    local_base_obj = datetime.strptime(
                        f"{local_today_str} {FIRST_TIME}", "%Y-%m-%d %H:%M"
                    ).replace(tzinfo=ZoneInfo(timezone))
                    local_end_obj = local_base_obj + timedelta(hours=DURATION_HOURS)
                    
                    time_diff = abs((now_local - local_end_obj).total_seconds() / 60)
                    if time_diff <= 5 and test_reminder_sent.get(chat_id) != local_today_str:
                        needs_processing = True
                except Exception as e:
                    if not PRODUCTION_MODE:
                        logger.error("Ошибка расчета времени теста для пользователя %s: %s", chat_id, e)
                
                if needs_processing:
                    process_user(user, now_server, bot, loop)
                    processed_count += 1
                    
                # Ограничиваем нагрузку
                if processed_count % 20 == 0:
                    asyncio.run_coroutine_threadsafe(asyncio.sleep(0.1), loop)
                    
            except Exception as e:
                if not PRODUCTION_MODE:
                    logger.error("Ошибка обработки пользователя %s: %s", chat_id, e)
                
    except Exception as e:
        logger.error("Критическая ошибка в планировщике: %s", e)
    
    # Сохранение времени последнего запуска
    try:
        from bot import save_last_run_time
        save_last_run_time(now_server)
    except Exception:
        pass

async def check_payments_job(bot: Bot):
    """Проверка активных платежей (оптимизированная)."""
    try:
        from services.payment import PaymentService
        processed_count = await PaymentService.check_all_active_payments(bot)
        
        if processed_count > 0:
            logger.info("Обработано платежей: %d", processed_count)
        
    except Exception as e:
        logger.error("Ошибка при проверке платежей: %s", e)

def reset_user_cache(chat_id=None):
    """Сброс кэша пользователей."""
    global user_cache, last_cache_update
    
    try:
        if chat_id is not None:
            user = crud.get_user(chat_id)
            if user:
                user_cache[chat_id] = user
            elif chat_id in user_cache:
                del user_cache[chat_id]
        else:
            user_cache = {}
            last_cache_update = 0
            
        if not PRODUCTION_MODE:
            logger.info("Кэш пользователей сброшен" + (f" для {chat_id}" if chat_id else ""))
            
    except Exception as e:
        logger.error("Ошибка сброса кэша: %s", e)

def process_daily_reset(chat_id):
    """Ежедневный сброс данных пользователя (оптимизированный)."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        reset_key = f"{chat_id}_reset_{today}"
        
        # Проверка на повторный сброс
        if hasattr(process_daily_reset, 'processed_resets') and reset_key in process_daily_reset.processed_resets:
            return
            
        if not hasattr(process_daily_reset, 'processed_resets'):
            process_daily_reset.processed_resets = set()
        
        # Обработка невыученных слов
        if chat_id in daily_words_cache:
            entry = daily_words_cache[chat_id]
            unique_words = entry[8] if len(entry) > 8 and entry[8] else []
            
            try:
                learned_raw = crud.get_learned_words(chat_id)
                learned_set = set(extract_english(item[0]).lower() for item in learned_raw)
                
                filtered_unique = []
                for word in unique_words:
                    english_part = extract_english(word).lower()
                    if english_part and english_part not in learned_set:
                        filtered_unique.append(word)
                
                if filtered_unique:
                    previous_daily_words[chat_id] = filtered_unique
                elif chat_id in previous_daily_words:
                    del previous_daily_words[chat_id]
                    
            except Exception as e:
                logger.error("Ошибка обработки выученных слов для пользователя %s: %s", chat_id, e)
                if unique_words:
                    previous_daily_words[chat_id] = unique_words
                
            reset_daily_words_cache(chat_id)
        
        # Сброс напоминания о тесте
        if chat_id in test_reminder_sent:
            del test_reminder_sent[chat_id]
        
        process_daily_reset.processed_resets.add(reset_key)
        
        # Очистка старых записей
        if len(process_daily_reset.processed_resets) > 1000:
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            today = datetime.now().strftime("%Y-%m-%d")
            process_daily_reset.processed_resets = {
                key for key in process_daily_reset.processed_resets 
                if today in key or yesterday in key
            }
            
        if not PRODUCTION_MODE:
            logger.info("Ежедневный сброс выполнен для пользователя %s", chat_id)
            
    except Exception as e:
        logger.error("Ошибка ежедневного сброса для пользователя %s: %s", chat_id, e)

def process_user(user, now_server, bot, loop):
    """Обработка отдельного пользователя (оптимизированная)."""
    chat_id = user[0]
    level = user[1]
    words_count = user[2]
    repetitions = user[3]
    
    user_tz = user[5] if len(user) > 5 and user[5] else "Europe/Moscow"
    try:
        ZoneInfo(user_tz)
        now_local = now_server.astimezone(ZoneInfo(user_tz))
    except Exception:
        user_tz = "Europe/Moscow"
        now_local = now_server.astimezone(ZoneInfo(user_tz))
    
    now_local_str = now_local.strftime("%H:%M")
    local_today_str = now_local.strftime("%Y-%m-%d")
    
    try:
        local_base_obj = datetime.strptime(
            f"{local_today_str} {FIRST_TIME}", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=ZoneInfo(user_tz))
        local_end_obj = local_base_obj + timedelta(hours=DURATION_HOURS)
    except Exception:
        return
    
    try:
        result = get_daily_words_for_user(
            chat_id, level, words_count, repetitions,
            first_time=FIRST_TIME, duration_hours=DURATION_HOURS
        )
        if result is None:
            return
        
        messages, times = result

        # Определение режима повторения
        is_revision_mode = False
        if chat_id in daily_words_cache:
            entry = daily_words_cache[chat_id]
            if len(entry) > 9:
                is_revision_mode = entry[9]

        # Отправка уведомлений
        if now_local_str in times:
            notif_index = times.index(now_local_str)
            message_text = messages[notif_index] if notif_index < len(messages) else "(нет слов)"
            
            try:
                asyncio.run_coroutine_threadsafe(
                    bot.send_message(chat_id, message_text),
                    loop
                )
                if not PRODUCTION_MODE:
                    logger.info("Отправлено уведомление пользователю %s в %s", chat_id, now_local_str)
            except Exception as e:
                logger.error("Ошибка отправки уведомления пользователю %s: %s", chat_id, e)
        
        # Напоминание о тесте
        try:
            current_time = now_local
            end_time = local_end_obj
            reminder_already_sent = test_reminder_sent.get(chat_id) == local_today_str
            time_diff_minutes = (end_time - current_time).total_seconds() / 60
            
            if 0 <= time_diff_minutes <= 15 and not reminder_already_sent:
                try:
                    if is_revision_mode:
                        reminder_message = "Пройдите тест для повторения выученных слов."
                    else:
                        reminder_message = "Пройдите тест, чтобы добавить слова в Ваш словарь."
                        
                    asyncio.run_coroutine_threadsafe(
                        bot.send_message(chat_id, reminder_message),
                        loop
                    )
                    test_reminder_sent[chat_id] = local_today_str
                    if not PRODUCTION_MODE:
                        logger.info("Отправлено напоминание о тесте пользователю %s", chat_id)
                except Exception as e:
                    logger.error("Ошибка отправки напоминания о тесте пользователю %s: %s", chat_id, e)
        except Exception as e:
            if not PRODUCTION_MODE:
                logger.error("Ошибка проверки времени теста для пользователя %s: %s", chat_id, e)
            
    except Exception as e:
        if not PRODUCTION_MODE:
            logger.error("Ошибка обработки слов дня для пользователя %s: %s", chat_id, e)

def start_scheduler(bot: Bot, loop: asyncio.AbstractEventLoop):
    """Запуск планировщика с оптимизированными настройками."""
    scheduler = AsyncIOScheduler()
    
    # Основная задача каждую минуту
    scheduler.add_job(scheduler_job, 'interval', minutes=1, args=[bot, loop])
    
    # Оптимизация БД раз в сутки (только в продакшене)
    if PRODUCTION_MODE:
        scheduler.add_job(
            lambda: asyncio.run_coroutine_threadsafe(optimize_database(), loop),
            'cron', hour=3, minute=0  # В 3:00 ночи
        )
    
    scheduler.start()
    mode = "PRODUCTION" if PRODUCTION_MODE else "DEVELOPMENT"
    logger.info("Планировщик запущен в режиме %s", mode)
    return scheduler

async def optimize_database():
    """Оптимизация базы данных (только для продакшена)."""
    try:
        from database.db import db_manager
        db_manager.optimize_db()
        logger.info("База данных оптимизирована")
    except Exception as e:
        logger.error("Ошибка оптимизации БД: %s", e)