#!/usr/bin/env python3
# broadcast.py - Скрипт для массовой рассылки сообщений всем пользователям бота

import asyncio
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

from aiogram import Bot
from aiogram.utils.exceptions import BotBlocked, ChatNotFound, TelegramAPIError, UserDeactivated

# Добавляем путь к проекту для импорта модулей
sys.path.insert(0, str(Path(__file__).parent))

from config import BOT_TOKEN
from database import crud
from database.db import db_manager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('broadcast.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class BroadcastManager:
    """Менеджер для массовой рассылки сообщений."""
    
    def __init__(self, bot_token: str):
        self.bot = Bot(token=bot_token, parse_mode="Markdown")
        self.stats = {
            'total': 0,
            'sent': 0,
            'failed': 0,
            'blocked': 0,
            'not_found': 0,
            'deactivated': 0,
            'other_errors': 0
        }
        
    async def get_all_users(self):
        """Получает список всех пользователей из базы данных."""
        try:
            users = crud.get_all_users()
            user_ids = [user[0] for user in users]  # Извлекаем chat_id
            logger.info(f"Найдено {len(user_ids)} пользователей в базе данных")
            return user_ids
        except Exception as e:
            logger.error(f"Ошибка получения списка пользователей: {e}")
            return []
    
    async def send_message_to_user(self, chat_id: int, message: str, delay: float = 0.05):
        """
        Отправляет сообщение одному пользователю с обработкой ошибок.
        
        Args:
            chat_id: ID чата пользователя
            message: Текст сообщения
            delay: Задержка между отправками (в секундах)
        """
        try:
            await self.bot.send_message(chat_id, message)
            self.stats['sent'] += 1
            logger.debug(f"Сообщение отправлено пользователю {chat_id}")
            
        except BotBlocked:
            self.stats['blocked'] += 1
            logger.debug(f"Пользователь {chat_id} заблокировал бота")
            
        except ChatNotFound:
            self.stats['not_found'] += 1
            logger.debug(f"Чат {chat_id} не найден")
            
        except UserDeactivated:
            self.stats['deactivated'] += 1
            logger.debug(f"Пользователь {chat_id} деактивирован")
            
        except TelegramAPIError as e:
            self.stats['other_errors'] += 1
            logger.warning(f"Telegram API ошибка для пользователя {chat_id}: {e}")
            
        except Exception as e:
            self.stats['failed'] += 1
            logger.error(f"Неожиданная ошибка для пользователя {chat_id}: {e}")
        
        finally:
            # Небольшая задержка для избежания rate limiting
            if delay > 0:
                await asyncio.sleep(delay)
    
    async def broadcast_message(self, message: str, batch_size: int = 30, delay: float = 1.0):
        """
        Отправляет сообщение всем пользователям с контролем скорости.
        
        Args:
            message: Текст сообщения для рассылки
            batch_size: Количество сообщений в батче
            delay: Задержка между батчами (в секундах)
        """
        users = await self.get_all_users()
        if not users:
            logger.error("Список пользователей пуст")
            return
        
        self.stats['total'] = len(users)
        logger.info(f"Начинаем рассылку {self.stats['total']} пользователям")
        
        start_time = time.time()
        
        # Разбиваем пользователей на батчи
        for i in range(0, len(users), batch_size):
            batch = users[i:i + batch_size]
            batch_number = i // batch_size + 1
            total_batches = (len(users) + batch_size - 1) // batch_size
            
            logger.info(f"Обрабатываем батч {batch_number}/{total_batches} ({len(batch)} пользователей)")
            
            # Отправляем сообщения в текущем батче
            tasks = []
            for chat_id in batch:
                task = self.send_message_to_user(chat_id, message, 0.03)  # 30ms между сообщениями
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
            # Показываем прогресс
            processed = min(i + batch_size, len(users))
            progress = (processed / len(users)) * 100
            logger.info(f"Прогресс: {processed}/{len(users)} ({progress:.1f}%)")
            
            # Задержка между батчами (кроме последнего)
            if i + batch_size < len(users):
                logger.info(f"Пауза {delay} секунд перед следующим батчем...")
                await asyncio.sleep(delay)
        
        # Выводим финальную статистику
        elapsed_time = time.time() - start_time
        self.print_statistics(elapsed_time)
    
    def print_statistics(self, elapsed_time: float):
        """Выводит статистику рассылки."""
        logger.info("=" * 50)
        logger.info("СТАТИСТИКА РАССЫЛКИ")
        logger.info("=" * 50)
        logger.info(f"Всего пользователей: {self.stats['total']}")
        logger.info(f"Успешно отправлено: {self.stats['sent']}")
        logger.info(f"Заблокировали бота: {self.stats['blocked']}")
        logger.info(f"Чат не найден: {self.stats['not_found']}")
        logger.info(f"Аккаунт деактивирован: {self.stats['deactivated']}")
        logger.info(f"Другие ошибки API: {self.stats['other_errors']}")
        logger.info(f"Неожиданные ошибки: {self.stats['failed']}")
        logger.info(f"Время выполнения: {elapsed_time:.1f} секунд")
        
        success_rate = (self.stats['sent'] / self.stats['total']) * 100 if self.stats['total'] > 0 else 0
        logger.info(f"Успешность доставки: {success_rate:.1f}%")
        logger.info("=" * 50)
    
    async def close(self):
        """Закрывает соединение с ботом."""
        await self.bot.session.close()

def get_message_from_user():
    """Получает сообщение для рассылки от пользователя."""
    print("\n" + "="*60)
    print("           СКРИПТ МАССОВОЙ РАССЫЛКИ")
    print("="*60)
    print()
    
    # Предустановленные шаблоны сообщений
    templates = {
        "1": {
            "name": "Обновление бота",
            "text": """🔄 *Обновление бота*

Уважаемые пользователи!

Мы выпустили новое обновление бота с улучшениями:
• Исправлены ошибки
• Улучшена стабильность
• Добавлены новые функции

Спасибо, что пользуетесь нашим ботом! 🙏"""
        },
        "2": {
            "name": "Техническое обслуживание", 
            "text": """⚙️ *Техническое обслуживание*

Уважаемые пользователи!

Сегодня с 02:00 до 04:00 (МСК) будет проводиться техническое обслуживание.

В это время бот может работать нестабильно.

Приносим извинения за неудобства! 🔧"""
        },
        "3": {
            "name": "Новая функция",
            "text":  """💰 Премиум-подписка = дополнительная мотивация и огромный выбор наборов слов по всем темам
            
Когда вы вкладываете деньги в обучение, вы автоматически становитесь более дисциплинированными. Это психология — мы не бросаем то, за что заплатили.

Подписку можно приобрести во вкладке Персонализация
"""
        },
        "4": {
            "name": "Пользовательское сообщение",
            "text": """💰 Премиум-подписка = дополнительная мотивация и огромный выбор наборов слов по всем темам

Когда вы вкладываете деньги в обучение, вы автоматически становитесь более дисциплинированными. Это психология — мы не бросаем то, за что заплатили.
Подписку можно приобрести во вкладке Персонализация
"""
        }
    }
    
    print("Выберите шаблон сообщения:")
    for key, template in templates.items():
        print(f"{key}. {template['name']}")
    print()
    
    choice = input("Введите номер шаблона (1-4): ").strip()
    
    if choice in templates:
        if choice == "4":
            print("\nВведите ваше сообщение (поддерживается Markdown):")
            print("Для завершения ввода наберите 'END' на новой строке")
            print("-" * 40)
            
            lines = []
            while True:
                line = input()
                if line.strip() == "END":
                    break
                lines.append(line)
            
            message = "\n".join(lines).strip()
        else:
            message = templates[choice]["text"]
            
        if not message:
            print("❌ Сообщение не может быть пустым!")
            return get_message_from_user()
            
    else:
        print("❌ Неверный выбор!")
        return get_message_from_user()
    
    # Предварительный просмотр
    print("\n" + "="*60)
    print("           ПРЕДВАРИТЕЛЬНЫЙ ПРОСМОТР")
    print("="*60)
    print(message)
    print("="*60)
    
    confirm = input("\nОтправить это сообщение всем пользователям? (y/N): ").strip().lower()
    
    if confirm in ['y', 'yes', 'да', 'д']:
        return message
    else:
        print("❌ Рассылка отменена")
        return None

async def main():
    """Основная функция скрипта."""
    try:
        # Проверяем токен бота
        if not BOT_TOKEN or BOT_TOKEN == "YOUR_DEFAULT_TOKEN":
            logger.error("❌ Токен бота не настроен в config.py")
            return
        
        # Получаем сообщение для рассылки
        message = get_message_from_user()
        if not message:
            return
        
        # Последнее подтверждение
        print(f"\n⚠️  ВНИМАНИЕ: Сейчас будет отправлено сообщение ВСЕМ пользователям бота!")
        final_confirm = input("Вы абсолютно уверены? Введите 'SEND' для подтверждения: ").strip()
        
        if final_confirm != "SEND":
            print("❌ Рассылка отменена")
            return
        
        # Создаем менеджер рассылки
        broadcast_manager = BroadcastManager(BOT_TOKEN)
        
        try:
            # Настройки рассылки
            batch_size = 30  # Количество сообщений в батче
            delay = 1.0      # Задержка между батчами в секундах
            
            logger.info("🚀 Начинаем массовую рассылку...")
            
            # Выполняем рассылку
            await broadcast_manager.broadcast_message(
                message=message,
                batch_size=batch_size,
                delay=delay
            )
            
            logger.info("✅ Рассылка завершена!")
            
        finally:
            # Закрываем соединения
            await broadcast_manager.close()
    
    except KeyboardInterrupt:
        logger.info("❌ Рассылка прервана пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Проверяем наличие необходимых файлов
    required_files = ["config.py", "database/crud.py", "database/db.py"]
    missing_files = [f for f in required_files if not Path(f).exists()]
    
    if missing_files:
        print(f"❌ Отсутствуют необходимые файлы: {', '.join(missing_files)}")
        print("Убедитесь, что скрипт запускается из корневой папки проекта")
        sys.exit(1)
    
    # Запускаем основную функцию
    asyncio.run(main())