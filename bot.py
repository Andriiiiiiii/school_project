# bot.py
import logging
from aiogram import Bot, Dispatcher, executor
from config import BOT_TOKEN
from services.scheduler import start_scheduler
from handlers import register_handlers
import asyncio

import pickle
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from config import SERVER_TIMEZONE

# Constants
LAST_RUN_FILE = "last_scheduler_run.pickle"
MAX_BACKFILL_HOURS = 3  # Maximum hours to look back for missed notifications

# Modified on_startup function in bot.py

async def on_startup(dp):
    loop = asyncio.get_running_loop()
    start_scheduler(bot, loop)
    
    # Установка команд бота для вызова меню
    from aiogram.types import BotCommand, BotCommandScopeDefault
    commands = [
        BotCommand(command="menu", description="Показать меню команд"),
        BotCommand(command="start", description="Перезапуск бота")
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    
    # Проверка пропущенных уведомлений
    await check_missed_notifications(bot)
    
    logger.info("Бот запущен")
    
# New function to check for missed notifications

async def check_missed_notifications(bot):
    """
    Проверяет и отправляет пропущенные уведомления при запуске бота.
    Вызывается при старте бота после простоя.
    """
    logger.info("Checking for missed notifications...")
    
    # Get current server time
    now_server = datetime.now(tz=ZoneInfo(SERVER_TIMEZONE))
    
    # Get last run time
    last_run_time = get_last_run_time()
    if not last_run_time:
        # If no previous run record, don't try to backfill
        save_last_run_time(now_server)
        return
    
    # Limit backfill to prevent spamming users after long downtimes
    earliest_check_time = now_server - timedelta(hours=MAX_BACKFILL_HOURS)
    if last_run_time < earliest_check_time:
        last_run_time = earliest_check_time
        
    try:
        # Get all users
        users = crud.get_all_users()
        processed_users = 0
        recovered_notifications = 0
        
        for user in users:
            try:
                chat_id = user[0]
                level = user[1]
                words_count = user[2]
                repetitions = user[3]
                timezone = user[5] if len(user) > 5 and user[5] else "Europe/Moscow"
                
                # Get local time for user
                try:
                    now_local = now_server.astimezone(ZoneInfo(timezone))
                    last_run_local = last_run_time.astimezone(ZoneInfo(timezone))
                except Exception:
                    logger.error(f"Invalid timezone {timezone} for user {chat_id}")
                    now_local = now_server.astimezone(ZoneInfo("Europe/Moscow"))
                    last_run_local = last_run_time.astimezone(ZoneInfo("Europe/Moscow"))
                
                # Get daily words and notification times
                result = get_daily_words_for_user(chat_id, level, words_count, repetitions,
                                               first_time=REMINDER_START, duration_hours=DURATION_HOURS)
                if result is None:
                    continue
                
                messages, times = result
                local_today = now_local.strftime("%Y-%m-%d")
                
                # Check if any notifications were missed
                missed_notifications = []
                for i, time_str in enumerate(times):
                    # Convert time string to datetime object
                    try:
                        notification_time = datetime.strptime(f"{local_today} {time_str}", 
                                                          "%Y-%m-%d %H:%M").replace(tzinfo=now_local.tzinfo)
                        
                        # If notification was scheduled between last run and now
                        if last_run_local < notification_time < now_local:
                            message_text = messages[i] if i < len(messages) else "(нет слов)"
                            missed_notifications.append((time_str, message_text))
                    except ValueError as e:
                        logger.error(f"Error parsing notification time {time_str} for user {chat_id}: {e}")
                        continue
                
                # If there are missed notifications, send them in a consolidated message
                if missed_notifications:
                    # Limit to last 3 missed notifications to avoid overwhelming
                    if len(missed_notifications) > 3:
                        missed_notifications = missed_notifications[-3:]
                    
                    consolidated_msg = "⚠️ Пропущенные уведомления во время простоя бота:\n\n"
                    for time_str, msg in missed_notifications:
                        consolidated_msg += f"📌 {time_str}:\n{msg}\n\n"
                    
                    await bot.send_message(chat_id, consolidated_msg)
                    logger.info(f"Sent {len(missed_notifications)} missed notifications to user {chat_id}")
                    recovered_notifications += len(missed_notifications)
                
                # Check if quiz reminder was missed
                try:
                    local_base_obj = datetime.strptime(f"{local_today} {REMINDER_START}", 
                                                    "%Y-%m-%d %H:%M").replace(tzinfo=now_local.tzinfo)
                    local_end_obj = local_base_obj + timedelta(hours=DURATION_HOURS)
                    
                    # If end time was between last run and now, and no reminder was sent today
                    if (last_run_local < local_end_obj < now_local and 
                        quiz_reminder_sent.get(chat_id) != local_today):
                        
                        # Check revision mode
                        is_revision_mode = False
                        if chat_id in daily_words_cache:
                            entry = daily_words_cache[chat_id]
                            if len(entry) > 9:
                                is_revision_mode = entry[9]
                        
                        # Send appropriate message
                        if is_revision_mode:
                            reminder_message = "⚠️ Пропущенное напоминание: Пройдите квиз для повторения выученных слов. Это поможет закрепить знания!"
                        else:
                            reminder_message = "⚠️ Пропущенное напоминание: Пройдите квиз, чтобы добавить слова в Ваш словарь."
                        
                        await bot.send_message(chat_id, reminder_message)
                        quiz_reminder_sent[chat_id] = local_today
                        logger.info(f"Sent missed quiz reminder to user {chat_id}")
                        recovered_notifications += 1
                except Exception as e:
                    logger.error(f"Error checking missed quiz reminder for user {chat_id}: {e}")
                
                processed_users += 1
                
                # Добавляем небольшую задержку между пользователями, чтобы не перегружать сервер
                if processed_users % 10 == 0:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error checking missed notifications for user {user[0]}: {e}")
        
        logger.info(f"Processed {processed_users} users, recovered {recovered_notifications} notifications")
    except Exception as e:
        logger.error(f"Error in check_missed_notifications: {e}")
    
    # Save current time as last run time
    save_last_run_time(now_server)

# Helper functions for tracking last run time

def get_last_run_time():
    """Reads the last scheduler run time from file."""
    try:
        if os.path.exists(LAST_RUN_FILE):
            with open(LAST_RUN_FILE, 'rb') as f:
                return pickle.load(f)
    except Exception as e:
        logger.error(f"Error reading last run time: {e}")
    return None

def save_last_run_time(time):
    """Saves the current scheduler run time to file."""
    try:
        with open(LAST_RUN_FILE, 'wb') as f:
            pickle.dump(time, f)
    except Exception as e:
        logger.error(f"Error saving last run time: {e}")

logging.basicConfig(
    level=logging.INFO,
    filename="logs/bot.log",
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

register_handlers(dp, bot)

# Запускаем планировщик после старта event loop
async def on_startup(dp):
    loop = asyncio.get_running_loop()
    start_scheduler(bot, loop)
    logger.info("Бот запущен.")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
