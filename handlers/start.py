# handlers/start.py
import logging
from aiogram import types
from keyboards.main_menu import main_menu_keyboard
from database import crud

logger = logging.getLogger(__name__)

async def cmd_start(message: types.Message):
    """
    Обработчик команды /start.
    Создает новую запись для пользователя в базе данных, если его еще нет.
    """
    chat_id = message.chat.id
    logger.info(f"Received /start from chat_id: {chat_id}")
    
    try:
        # Проверяем существует ли пользователь
        user = crud.get_user(chat_id)
        if not user:
            # Если нет - создаем запись
            crud.add_user(chat_id)
            logger.info(f"Added new user with chat_id {chat_id}")
        else:
            logger.info(f"User {chat_id} already exists")
        
        # Отправляем приветственное сообщение
        await message.answer(
            "Добро пожаловать в English Learning Bot!\n\nВыберите действие:",
            reply_markup=main_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in cmd_start for chat_id {chat_id}: {e}")
        # В случае ошибки все равно пытаемся отправить меню
        await message.answer(
            "Произошла ошибка при инициализации профиля. Пожалуйста, повторите попытку позже.\n\nВыберите действие:",
            reply_markup=main_menu_keyboard()
        )