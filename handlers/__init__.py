# handlers/__init__.py
from .start import cmd_start
from .words import register_words_handlers
from .settings import register_settings_handlers
from .premium import register_premium_handlers

def register_handlers(dp, bot):
    dp.register_message_handler(cmd_start, commands=['start'])
    register_words_handlers(dp, bot)
    register_settings_handlers(dp, bot)
    register_premium_handlers(dp, bot)
