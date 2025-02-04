# handlers/premium.py
from aiogram import types, Bot

async def premium_feature(message: types.Message, bot: Bot):
    await bot.send_message(message.chat.id, "Эта функция доступна только для премиум пользователей. (В разработке)")

# Обёртка для message-обработчика
async def premium_feature_handler(message: types.Message):
    await premium_feature(message, message.bot)

def register_premium_handlers(dp, bot: Bot):
    dp.register_message_handler(premium_feature_handler, commands=['premium'])
