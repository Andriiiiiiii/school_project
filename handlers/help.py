# handlers/help.py

from aiogram import types, Dispatcher, Bot
from keyboards.submenus import help_menu_keyboard
from keyboards.main_menu import main_menu_keyboard
from functools import partial

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
    
    await callback.message.edit_text(
        help_text,
        parse_mode="Markdown",
        reply_markup=help_menu_keyboard()
    )
    await callback.answer()

async def process_help_about_callback(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик кнопки "О боте" из меню помощи.
    """
    about_text = (
        "ℹ️ *Как работает бот* ℹ️\n\n"
        "*Принцип обучения:*\n"
        "1️⃣ Получайте слова дня в уведомлениях\n"
        "2️⃣ Проходите квизы для проверки знаний\n"
        "3️⃣ Правильные ответы добавляются в словарь\n"
        "4️⃣ Невыученные слова повторяются завтра\n"
        "5️⃣ После изучения всех слов — режим повторения\n\n"
        
        "*Начало работы:*\n"
        "➡️ Выберите уровень в Настройках\n"
        "➡️ Установите количество слов в день\n"
        "➡️ Перейдите в раздел Слова дня"
    )
    
    await callback.message.edit_text(
        about_text,
        parse_mode="Markdown",
        reply_markup=help_menu_keyboard()
    )
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
    
    await callback.message.edit_text(
        commands_text,
        parse_mode="Markdown",
        reply_markup=help_menu_keyboard()
    )
    await callback.answer()

async def process_help_tips_callback(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик кнопки "Советы" из меню помощи.
    """
    tips_text = (
        "💡 *Советы для эффективного изучения* 💡\n\n"
        
        "✅ Проходите квизы каждый день\n"
        "✅ Начните с 5-10 слов в день\n"
        "✅ Используйте 3-5 повторений\n"
        "✅ Регулярно проверяйте словарь\n"
        "✅ Постепенно увеличивайте нагрузку\n"
        "✅ Изучайте уровни последовательно (A1→A2→B1...)\n"
        "✅ Отслеживайте прогресс в профиле\n\n"
        
        "*Рекомендуемые настройки для начала:*\n"
        "• Уровень: ваш текущий уровень владения языком\n"
        "• Слов в день: 5\n"
        "• Повторений: 3"
    )
    
    await callback.message.edit_text(
        tips_text,
        parse_mode="Markdown",
        reply_markup=help_menu_keyboard()
    )
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
    
    await callback.message.edit_text(
        feedback_text,
        parse_mode="Markdown",
        reply_markup=help_menu_keyboard()
    )
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