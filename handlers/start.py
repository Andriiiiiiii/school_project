# handlers/start.py
from aiogram import types
from keyboards.main_menu import main_menu_keyboard
from database import crud  # или используйте функции из вашего модуля database

async def cmd_start(message: types.Message):
    chat_id = message.chat.id
    crud.add_user(chat_id)
    await message.answer(
        "Добро пожаловать в English Learning Bot!\n\nВыберите действие из меню ниже:",
        reply_markup=main_menu_keyboard()
    )

