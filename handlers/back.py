# handlers/back.py
from aiogram import types
from keyboards.main_menu import main_menu_keyboard

async def handle_back(callback: types.CallbackQuery):
    """
    Обработчик кнопки «Назад».
    Редактирует сообщение (или отправляет новое) с главным меню.
    """
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()
