# handlers/start.py
import logging
from aiogram import types
from keyboards.main_menu import main_menu_keyboard
from database import crud

logger = logging.getLogger(__name__)

async def cmd_start(message: types.Message):
    chat_id = message.chat.id
    logger.info(f"Received /start from chat_id: {chat_id}")
    crud.add_user(chat_id)
    await message.answer(
        "Добро пожаловать в English Learning Bot!\n\nВыберите действие:",
        reply_markup=main_menu_keyboard()
    )
