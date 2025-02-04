# handlers/dictionary.py
from aiogram import types, Dispatcher, Bot
from database import crud
from keyboards.main_menu import main_menu_keyboard

async def show_dictionary(chat_id: int, bot: Bot):
    words = crud.get_user_dictionary(chat_id)
    if not words:
        await bot.send_message(chat_id, "Ваш словарь пуст.", reply_markup=main_menu_keyboard())
    else:
        text = "Ваш словарь:\n\n"
        for word, translation, transcription, example in words:
            text += f"• {word} — {translation}\n"
        await bot.send_message(chat_id, text, reply_markup=main_menu_keyboard())

def register_dictionary_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(lambda c: c.data == "menu:my_dictionary", lambda c: show_dictionary(c.from_user.id, bot))
    dp.register_message_handler(lambda message: show_dictionary(message.chat.id, bot), commands=["dictionary"])
