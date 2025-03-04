#handlers/init.py

from .start import cmd_start
from .words import register_words_handlers
from .learning import register_learning_handlers
from .dictionary import register_dictionary_handlers
from .settings import register_settings_handlers
from .help import register_help_handlers
from .back import handle_back  # обработчик кнопки "Назад"
from .test_level import register_level_test_handlers
from .quiz import register_quiz_handlers

def register_handlers(dp, bot):
    dp.register_message_handler(cmd_start, commands=["start"])
    register_words_handlers(dp, bot)
    register_learning_handlers(dp, bot)
    register_dictionary_handlers(dp, bot)
    register_settings_handlers(dp, bot)
    register_help_handlers(dp, bot)
    dp.register_callback_query_handler(handle_back, lambda c: c.data == "menu:back")
    register_level_test_handlers(dp, bot)
    register_quiz_handlers(dp, bot)
