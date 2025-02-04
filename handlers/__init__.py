# handlers/__init__.py
from .start import cmd_start
from .words import register_words_handlers
from .dictionary import register_dictionary_handlers
from .help import register_help_handlers
from .settings import register_settings_handlers
from .quiz import register_quiz_handlers
from .test import register_test_handlers

def register_handlers(dp, bot):
    dp.register_message_handler(cmd_start, commands=['start'])
    # Регистрируем обработчики для каждого раздела
    register_words_handlers(dp, bot)
    register_dictionary_handlers(dp, bot)
    register_help_handlers(dp, bot)
    register_settings_handlers(dp, bot)
    register_quiz_handlers(dp, bot)
    register_test_handlers(dp, bot)
