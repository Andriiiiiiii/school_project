# handlers/premium.py
from aiogram import types, Bot

async def premium_feature(message: types.Message, bot: Bot):
    await bot.send_message(message.chat.id, "Эта функция доступна только для премиум пользователей. (В разработке)")

def register_premium_handlers(dp, bot: Bot):
    dp.register_message_handler(lambda message: premium_feature(message, bot), commands=['premium'])
