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
from .onboarding import register_onboarding_handlers
from .subscription import register_subscription_handlers  # Добавить эту строку
from .referrals import register_referral_handlers


def register_handlers(dp: Dispatcher, bot: Bot) -> None:
    """Регистрирует все обработчики в нужном порядке."""
    # 0. Онбординг для новых пользователей
    register_onboarding_handlers(dp, bot)
    
    # 1. Poll-квизы и режим «Обучение»
    register_quiz_handlers(dp, bot)
    register_learning_handlers(dp, bot)

    # 2. Основные разделы
    register_command_handlers(dp, bot)
    register_words_handlers(dp, bot)
    register_dictionary_handlers(dp, bot)
    register_settings_handlers(dp, bot)
    register_help_handlers(dp, bot)

    # 3. Подписка и рефералы
    register_subscription_handlers(dp, bot)
    register_referral_handlers(dp, bot)  # Добавить эту строку

    # 4. Навигация «Назад»
    dp.register_callback_query_handler(
        handle_back,
        lambda c: c.data == "menu:back"
    )