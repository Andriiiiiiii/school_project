# handlers/help.py

import logging
from aiogram import types, Dispatcher, Bot
from aiogram.utils.exceptions import MessageNotModified
from keyboards.submenus import help_menu_keyboard
from keyboards.main_menu import main_menu_keyboard
from functools import partial

logger = logging.getLogger(__name__)

async def show_help_callback(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик кнопки "Помощь" из главного меню.
    Отображает основную информацию о боте.
    """
    help_text = (
        "📚 *English Learning Bot* 📚\n\n"
        "Бот поможет вам эффективно изучать английские слова. Основные разделы:\n\n"
        
        "📌 *Слова дня* — ежедневные слова с уведомлениями\n"
        "📝 *Тест дня* — проверка знания слов\n"
        "📖 *Мой словарь* — ваши выученные слова\n"
        "🏋️ *Практика* — дополнительные тренировки\n"
        "🏠 *Персонализация* — настройка бота\n\n"
        
        "Выберите раздел для получения подробной информации:"
    )
    
    try:
        await callback.message.edit_text(
            help_text,
            parse_mode="Markdown",
            reply_markup=help_menu_keyboard()
        )
    except MessageNotModified:
        logger.debug(f"Help message not modified for user {callback.from_user.id}")
        pass  # Игнорируем, если сообщение не изменилось
    except Exception as e:
        logger.error(f"Error editing help message for user {callback.from_user.id}: {e}")
        # В случае другой ошибки, отправляем новое сообщение
        try:
            await bot.send_message(
                callback.from_user.id,
                help_text,
                parse_mode="Markdown",
                reply_markup=help_menu_keyboard()
            )
        except Exception as send_error:
            logger.error(f"Failed to send fallback help message: {send_error}")
    
    await callback.answer()

async def process_help_about_callback(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик кнопки "О боте" из меню помощи.
    """
    about_text = (
        "ℹ️ *О боте и как им пользоваться* ℹ️\n\n"
        
        "*🎯 Главная идея:*\n"
        "Бот помогает учить английские слова маленькими порциями каждый день\n\n"
        
        "*📚 Что такое набор слов?*\n"
        "Это готовая подборка из ~50 английских слов по темам и уровням.\n"
        "Примеры:\n"
        "• «A1 Basic 1» — базовые слова для начинающих (~50 слов)\n"
        "• «B1 Travel» — слова про путешествия (~50 слов)\n"
        "• «B2 Business» — бизнес лексика (~50 слов)\n\n"
        
        "*🔄 Как происходит обучение:*\n"
        "1️⃣ Утром вы получаете порцию слов из выбранного набора\n"
        "2️⃣ В течение дня слова повторяются в уведомлениях\n"
        "3️⃣ Вечером проходите тест дня\n"
        "4️⃣ ✅ Правильные ответы → слова в ваш словарь\n"
        "5️⃣ ❌ Неправильные → повторятся завтра\n\n"
        
        "*💡 Когда выучите весь набор (~50 слов):*\n"
        "Бот перейдет в режим повторения изученных слов\n"
        "или вы можете выбрать новый набор в настройках"
    )
    
    try:
        await callback.message.edit_text(
            about_text,
            parse_mode="Markdown",
            reply_markup=help_menu_keyboard()
        )
    except MessageNotModified:
        logger.debug(f"About message not modified for user {callback.from_user.id}")
        pass  # Игнорируем, если сообщение не изменилось
    except Exception as e:
        logger.error(f"Error editing about message for user {callback.from_user.id}: {e}")
        try:
            await bot.send_message(
                callback.from_user.id,
                about_text,
                parse_mode="Markdown",
                reply_markup=help_menu_keyboard()
            )
        except Exception as send_error:
            logger.error(f"Failed to send fallback about message: {send_error}")
    
    await callback.answer()
    
async def process_help_commands_callback(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик кнопки "Разделы бота" из меню помощи.
    """
    commands_text = (
        "🔍 *Разделы бота* 🔍\n\n"
        
        "📌 *Слова дня*\n"
        "Ежедневные слова для изучения с уведомлениями. Настраивается количество слов и повторений.\n\n"
        
        "📝 *Тест дня*\n"
        "Тестирует знание ваших слов дня. Правильные ответы добавляются в словарь.\n\n"
        
        "📖 *Мой словарь*\n"
        "Все выученные слова. Сбрасывается при смене набора слов.\n\n"
        
        "🏋️ *Практика*\n"
        "Тесты по словарю и режим заучивания случайных слов из выбранного набора.\n\n"
        
        "🏠 *Персонализация*\n"
        "Уровень, количество слов, частота повторений, набор слов, часовой пояс."
    )
    
    try:
        await callback.message.edit_text(
            commands_text,
            parse_mode="Markdown",
            reply_markup=help_menu_keyboard()
        )
    except MessageNotModified:
        logger.debug(f"Commands message not modified for user {callback.from_user.id}")
        pass
    except Exception as e:
        logger.error(f"Error editing commands message for user {callback.from_user.id}: {e}")
        try:
            await bot.send_message(
                callback.from_user.id,
                commands_text,
                parse_mode="Markdown",
                reply_markup=help_menu_keyboard()
            )
        except Exception as send_error:
            logger.error(f"Failed to send fallback commands message: {send_error}")
    
    await callback.answer()

async def process_help_tips_callback(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик кнопки "Советы" из меню помощи.
    """
    tips_text = (
        "💡 *Советы для эффективного изучения* 💡\n\n"
        
        "✅ Проходите тесты дня ежедневно\n"
        "✅ Начните с 4-6 слов в день\n"
        "✅ Используйте 2-3 повторений\n"
        "✅ Регулярно проверяйте словарь\n"
        "✅ Практикуйте тесты по набору и словарю\n"
        "✅ Изучайте разные наборы слов\n"
        "✅ Изучайте уровни последовательно (A1→A2→B1...)\n"
        "✅ Отслеживайте прогресс в профиле\n\n"
        
        "*Рекомендуемые настройки для начала:*\n"
        "• Уровень: ваш текущий уровень владения языком\n"
        "• Слов в день: 5\n"
        "• Повторений: 3"
    )
    
    try:
        await callback.message.edit_text(
            tips_text,
            parse_mode="Markdown",
            reply_markup=help_menu_keyboard()
        )
    except MessageNotModified:
        logger.debug(f"Tips message not modified for user {callback.from_user.id}")
        pass
    except Exception as e:
        logger.error(f"Error editing tips message for user {callback.from_user.id}: {e}")
        try:
            await bot.send_message(
                callback.from_user.id,
                tips_text,
                parse_mode="Markdown",
                reply_markup=help_menu_keyboard()
            )
        except Exception as send_error:
            logger.error(f"Failed to send fallback tips message: {send_error}")
    
    await callback.answer()

async def process_help_feedback_callback(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик кнопки "Обратная связь" из меню помощи.
    """
    feedback_text = (
        "✉️ *Обратная связь* ✉️\n\n"
        "У вас есть вопросы или предложения?\n\n"
        
        "• Telegram: @username\n"
        "• Email: support@example.com\n\n"
        
        "Мы регулярно обновляем бота и добавляем новые функции, основываясь на отзывах пользователей."
    )
    
    try:
        await callback.message.edit_text(
            feedback_text,
            parse_mode="Markdown",
            reply_markup=help_menu_keyboard()
        )
    except MessageNotModified:
        logger.debug(f"Feedback message not modified for user {callback.from_user.id}")
        pass
    except Exception as e:
        logger.error(f"Error editing feedback message for user {callback.from_user.id}: {e}")
        try:
            await bot.send_message(
                callback.from_user.id,
                feedback_text,
                parse_mode="Markdown",
                reply_markup=help_menu_keyboard()
            )
        except Exception as send_error:
            logger.error(f"Failed to send fallback feedback message: {send_error}")
    
    await callback.answer()

def register_help_handlers(dp: Dispatcher, bot: Bot):
    """
    Регистрирует обработчики для меню помощи.
    """
    dp.register_callback_query_handler(
        partial(show_help_callback, bot=bot),
        lambda c: c.data == "menu:help"
    )
    dp.register_callback_query_handler(
        partial(process_help_about_callback, bot=bot),
        lambda c: c.data == "help:about"
    )
    dp.register_callback_query_handler(
        partial(process_help_commands_callback, bot=bot),
        lambda c: c.data == "help:commands"
    )
    dp.register_callback_query_handler(
        partial(process_help_tips_callback, bot=bot),
        lambda c: c.data == "help:tips"
    )
    dp.register_callback_query_handler(
        partial(process_help_feedback_callback, bot=bot),
        lambda c: c.data == "help:feedback"
    )