# services/scheduler.py

import random
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import asyncio
import logging
from aiogram import Bot
from zoneinfo import ZoneInfo
from database import crud
from utils.helpers import get_daily_words_for_user, daily_words_cache, previous_daily_words, reset_daily_words_cache, extract_english
from config import REMINDER_START, DURATION_HOURS, SERVER_TIMEZONE, DAILY_RESET_TIME

logger = logging.getLogger(__name__)
FIRST_TIME = REMINDER_START

# Словарь для отслеживания, было ли отправлено напоминание по квизу для каждого пользователя за текущий день
quiz_reminder_sent = {}

# Кэш информации о пользователях для сокращения запросов к БД
user_cache = {}
# Время последнего обновления кэша (в формате временной метки)
last_cache_update = 0
# Интервал обновления кэша в секундах (каждые 15 минут)
CACHE_UPDATE_INTERVAL = 15 * 60

def scheduler_job(bot: Bot, loop: asyncio.AbstractEventLoop):
    """
    Оптимизированная функция, вызываемая каждую минуту.
    Использует кэширование и оптимизации для снижения нагрузки на БД.
    """
    global last_cache_update, user_cache
    
    try:
        # Получаем серверное время с установленной временной зоной
        try:
            now_server = datetime.now(tz=ZoneInfo(SERVER_TIMEZONE))
        except Exception as e:
            logger.error(f"Ошибка при установке серверной временной зоны {SERVER_TIMEZONE}: {e}")
            now_server = datetime.now(tz=ZoneInfo("UTC"))  # Используем UTC как запасной вариант
        
        current_time = now_server.timestamp()
        
        # Обновляем кэш пользователей, если прошло достаточно времени
        if current_time - last_cache_update > CACHE_UPDATE_INTERVAL:
            try:
                user_cache = {user[0]: user for user in crud.get_all_users()}
                last_cache_update = current_time
                logger.debug(f"Updated user cache with {len(user_cache)} users")
            except Exception as e:
                logger.error(f"Error updating user cache: {e}")
                # В случае ошибки, все равно используем имеющиеся данные
                if not user_cache:
                    # Только если кэш пуст, пытаемся получить свежие данные
                    try:
                        user_cache = {user[0]: user for user in crud.get_all_users()}
                    except Exception as e2:
                        logger.error(f"Failed to get users after cache update error: {e2}")
                        user_cache = {}
        
        # Если нет пользователей, нечего обрабатывать
        if not user_cache:
            return
            
        # Получаем текущую минуту для оптимизации проверок
        current_minute_str = now_server.strftime("%M")
        
        # Обрабатываем каждого пользователя
        for chat_id, user in user_cache.items():
            try:
                # Определяем часовой пояс пользователя
                timezone = user[5] if len(user) > 5 and user[5] else "Europe/Moscow"
                
                # Получаем локальное время для пользователя
                try:
                    now_local = now_server.astimezone(ZoneInfo(timezone))
                except Exception:
                    now_local = now_server.astimezone(ZoneInfo("Europe/Moscow"))
                    
                # Получаем строку часа и минуты для проверки уведомлений
                now_local_str = now_local.strftime("%H:%M")
                
                hour_minute = now_local.hour * 60 + now_local.minute
                if 0 <= hour_minute <= 3:  # От 00:00 до 00:03
                    process_daily_reset(chat_id)
                    continue  # Пропускаем дальнейшую обработку
                
                # Полная обработка пользователя только если наступило точное время уведомления
                # или время для проверки квиза (близкое к концу периода)
                needs_processing = False
                
                # Проверяем, есть ли уведомления в текущее время
                try:
                    # Получаем данные для слов дня с минимальной обработкой
                    result = get_daily_words_for_user(chat_id, user[1], user[2], user[3],
                                                 first_time=FIRST_TIME, duration_hours=DURATION_HOURS)
                    if result:
                        messages, times = result
                        # Если текущее время есть в списке запланированных, обрабатываем
                        if now_local_str in times:
                            needs_processing = True
                except Exception as e:
                    logger.error(f"Error checking notification times for user {chat_id}: {e}")
                
                # Вычисляем время для отправки напоминания о квизе
                try:
                    local_today_str = now_local.strftime("%Y-%m-%d")
                    local_base_obj = datetime.strptime(f"{local_today_str} {FIRST_TIME}", "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(timezone))
                    local_end_obj = local_base_obj + timedelta(hours=DURATION_HOURS)
                    
                    # Проверяем, близко ли текущее время к окончанию периода (в пределах 3 минут)
                    time_diff = abs((now_local - local_end_obj).total_seconds() / 60)
                    if time_diff <= 3 and quiz_reminder_sent.get(chat_id) != local_today_str:
                        needs_processing = True
                except Exception as e:
                    logger.error(f"Error calculating quiz reminder time for user {chat_id}: {e}")
                
                # Только если требуется обработка, вызываем полную функцию
                if needs_processing:
                    process_user(user, now_server, bot, loop)
            except Exception as e:
                logger.error(f"Error processing user {chat_id}: {e}")
    except Exception as e:
        logger.error(f"Unhandled error in scheduler_job: {e}")
    
    try:
        # Попытка сохранить время последнего запуска
        from bot import save_last_run_time  # Импортируем здесь, чтобы избежать циклических импортов
        save_last_run_time(now_server)
    except Exception as e:
        logger.error(f"Error saving scheduler run time: {e}")

def process_daily_reset(chat_id):
    """Обработка ежедневного сброса данных для пользователя."""
    try:
        # Улучшенная обработка невыученных слов
        if chat_id in daily_words_cache:
            entry = daily_words_cache[chat_id]
            unique_words = entry[8] if len(entry) > 8 and entry[8] else []  # список уникальных слов текущего дня
            
            # Получаем выученные слова
            try:
                learned_raw = crud.get_learned_words(chat_id)
                # Создаем множество выученных слов, приводя все к нижнему регистру
                learned_set = set(extract_english(item[0]).lower() for item in learned_raw)
                
                # Фильтруем уникальные слова, оставляя только невыученные
                filtered_unique = []
                for word in unique_words:
                    # Используем улучшенную функцию extract_english для извлечения словарной формы
                    english_part = extract_english(word).lower()
                    if english_part and english_part not in learned_set:
                        filtered_unique.append(word)
                
                # Сохраняем невыученные слова для следующего дня
                if filtered_unique:
                    previous_daily_words[chat_id] = filtered_unique
                    logger.info(f"Сохранено {len(filtered_unique)} невыученных слов для пользователя {chat_id}")
                elif chat_id in previous_daily_words:
                    # Если все слова выучены, удаляем запись
                    del previous_daily_words[chat_id]
                    logger.info(f"Все слова выучены, запись удалена для пользователя {chat_id}")
            except Exception as e:
                logger.error(f"Ошибка при получении выученных слов для пользователя {chat_id}: {e}")
                # В случае ошибки сохраняем все слова
                if unique_words:
                    previous_daily_words[chat_id] = unique_words
                    logger.warning(f"Из-за ошибки сохранены все {len(unique_words)} слов для пользователя {chat_id}")
                
            # Сбрасываем кэш для генерации нового списка слов на завтра
            reset_daily_words_cache(chat_id)
            logger.info(f"Кэш сброшен для пользователя {chat_id}")
        
        # Сбрасываем флаг напоминания
        if chat_id in quiz_reminder_sent:
            del quiz_reminder_sent[chat_id]
            
        logger.info(f"Daily reset completed for user {chat_id}")
    except Exception as e:
        logger.error(f"Error processing daily reset for user {chat_id}: {e}")

def process_user(user, now_server, bot, loop):
    """
    Обрабатывает одного пользователя в планировщике.
    Вынесено в отдельную функцию для лучшей изоляции ошибок.
    """
    chat_id = user[0]
    level = user[1]
    words_count = user[2]
    repetitions = user[3]
    
    # Безопасно получаем часовой пояс пользователя с проверкой на валидность
    user_tz = user[5] if len(user) > 5 and user[5] else "Europe/Moscow"
    try:
        # Проверяем валидность часового пояса
        ZoneInfo(user_tz)
        now_local = now_server.astimezone(ZoneInfo(user_tz))
    except Exception as e:
        # В случае ошибки используем значение по умолчанию
        logger.error(f"Неверный часовой пояс {user_tz} для пользователя {chat_id}: {e}")
        user_tz = "Europe/Moscow"
        try:
            now_local = now_server.astimezone(ZoneInfo(user_tz))
            # Обновляем часовой пояс пользователя на корректное значение
            crud.update_user_timezone(chat_id, user_tz)
        except Exception as e2:
            logger.critical(f"Критическая ошибка с часовым поясом: {e2}")
            now_local = now_server  # Используем серверное время как крайний случай
    
    now_local_str = now_local.strftime("%H:%M")
    local_today_str = now_local.strftime("%Y-%m-%d")
    
    # Вычисляем базовое локальное время начала и окончания периода
    try:
        local_base_obj = datetime.strptime(f"{local_today_str} {FIRST_TIME}", "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(user_tz))
        local_end_obj = local_base_obj + timedelta(hours=DURATION_HOURS)
        end_time_str = local_end_obj.strftime("%H:%M")
    except Exception as e:
        logger.error(f"Ошибка вычисления времен для пользователя {chat_id}: {e}")
        return
    
    # Получаем список слов дня (это также обновляет кэш, если необходимо)
    try:
        result = get_daily_words_for_user(chat_id, level, words_count, repetitions,
                                         first_time=FIRST_TIME, duration_hours=DURATION_HOURS)
        if result is None:
            return
        messages, times = result

        # Проверяем, находимся ли мы в режиме повторения
        is_revision_mode = False
        if chat_id in daily_words_cache:
            entry = daily_words_cache[chat_id]
            if len(entry) > 9:  # Проверяем наличие флага режима повторения
                is_revision_mode = entry[9]

        # Отправка обычных уведомлений по расписанию
        if now_local_str in times:
            notif_index = times.index(now_local_str)
            message_text = messages[notif_index] if notif_index < len(messages) else "(нет слов)"
            try:
                asyncio.run_coroutine_threadsafe(
                    bot.send_message(chat_id, f"📌 Слова дня:\n{message_text}"),
                    loop
                )
                logger.info(f"Sent notification to user {chat_id} at {now_local_str}")
            except Exception as e:
                logger.error(f"Error sending notification to user {chat_id}: {e}")
        
        # ИСПРАВЛЕННЫЙ КОД: Используем временное окно вместо точного сравнения
        # Вычисляем разницу в минутах между текущим временем и временем окончания
        try:
            # Преобразуем текущее время и время окончания в datetime-объекты для корректного сравнения
            current_time = now_local
            end_time = local_end_obj
            
            # Проверяем, не отправляли ли мы уже напоминание сегодня
            reminder_already_sent = quiz_reminder_sent.get(chat_id) == local_today_str
            
            # Отправляем напоминание, если мы в пределах 10 минут от конца и еще не отправляли сегодня
            time_diff_minutes = (end_time - current_time).total_seconds() / 60
            
            if 0 <= time_diff_minutes <= 10 and not reminder_already_sent:
                try:
                    # Адаптируем сообщение в зависимости от режима (обычный/повторение)
                    if is_revision_mode:
                        reminder_message = "Пройдите квиз для повторения выученных слов. Это поможет закрепить знания!"
                    else:
                        reminder_message = "Пройдите квиз, чтобы добавить слова в Ваш словарь."
                        
                    asyncio.run_coroutine_threadsafe(
                        bot.send_message(chat_id, reminder_message),
                        loop
                    )
                    quiz_reminder_sent[chat_id] = local_today_str
                    logger.info(f"Sent quiz reminder to user {chat_id}")
                except Exception as e:
                    logger.error(f"Error sending quiz reminder to user {chat_id}: {e}")
        except Exception as e:
            logger.error(f"Error checking quiz reminder time for user {chat_id}: {e}")
            
    except Exception as e:
        logger.error(f"Error processing daily words for user {chat_id}: {e}")

def start_scheduler(bot: Bot, loop: asyncio.AbstractEventLoop):
    """
    Запускает APScheduler, который каждую минуту вызывает scheduler_job.
    Оптимизированная версия с более умной логикой.
    """
    scheduler = AsyncIOScheduler()
    
    # Запускаем основную задачу каждую минуту для точности
    scheduler.add_job(scheduler_job, 'interval', minutes=1, args=[bot, loop])
    
    scheduler.start()
    logger.info("Scheduler started with optimized configuration")
    return scheduler