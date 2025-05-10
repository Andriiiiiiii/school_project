# handlers/__init__.py
"""
Регистрирует все обработчики бота.
"""

from aiogram import Dispatcher, Bot

from .commands import register_command_handlers, set_commands
from .words import register_words_handlers
from .learning import register_learning_handlers
from .quiz import register_quiz_handlers
from .dictionary import register_dictionary_handlers
from .settings import register_settings_handlers
from .help import register_help_handlers
from .back import handle_back


def register_handlers(dp: Dispatcher, bot: Bot) -> None:
    """
    Регистрирует все обработчики в нужном порядке:
      1. Poll-квизы и обучение
      2. Основные разделы
      3. Навигация «Назад» и тест уровня
    """
    # 1. Poll-квизы и режим «Обучение» (включая тест по словарю)
    register_quiz_handlers(dp, bot)
    register_learning_handlers(dp, bot)

    # 2. Основные разделы
    register_command_handlers(dp, bot)
    register_words_handlers(dp, bot)
    register_dictionary_handlers(dp, bot)
    register_settings_handlers(dp, bot)
    register_help_handlers(dp, bot)

    # 3. Навигация «Назад»
    dp.register_callback_query_handler(
        handle_back,
        lambda c: c.data == "menu:back"
    )

