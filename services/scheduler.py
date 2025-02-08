# services/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import asyncio

def scheduler_job(bot):
    # Получаем текущее время в формате HH:MM
    now = datetime.now().strftime("%H:%M")
    # Пример: если время между 10:00 и 22:00, можно отправлять уведомления.
    if "10:00" <= now <= "22:00":
        # Здесь вызываем функцию отправки слов дня
        # Например, проходим по списку пользователей и отправляем слово
        # (Эту логику нужно реализовать, используя базу данных)
        pass
    # В 22:00 можно запустить викторину
    if now == "22:00":
        # Запустить вечернюю викторину для всех пользователей
        pass

def start_scheduler(bot):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(scheduler_job, 'interval', minutes=1, args=[bot])
    scheduler.start()
    return scheduler
