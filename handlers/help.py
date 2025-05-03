# handlers/help.py

from aiogram import types, Dispatcher, Bot
from keyboards.submenus import help_menu_keyboard
from keyboards.main_menu import main_menu_keyboard
from functools import partial

async def show_help_callback(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик кнопки "Помощь" из главного меню.
    Отображает основную информацию о боте и возможностях обучения.
    """
    help_text = (
        "📚 *Добро пожаловать в English Learning Bot!* 📚\n\n"
        "Этот бот поможет вам эффективно изучать английские слова с помощью следующих функций:\n\n"
        
        "🔸 *Слова дня* — ежедневный набор слов для изучения, которые вы будете получать в уведомлениях в течение дня\n\n"
        
        "🔸 *Квиз* — тест по словам дня, который поможет проверить ваши знания и добавить правильно отвеченные слова в ваш личный словарь\n\n"
        
        "🔸 *Обучение* — дополнительные тесты по словарю и возможность заучивания отдельных наборов слов\n\n"
        
        "🔸 *Мой словарь* — ваша личная коллекция выученных слов, которая пополняется при правильных ответах в квизе\n\n"
        
        "🔸 *Настройки* — настройте свой уровень, ежедневное количество слов, тип набора слов, часовой пояс и другие параметры\n\n"
        
        "Выберите раздел для получения дополнительной информации:"
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
    Предоставляет подробную информацию о боте и его возможностях.
    """
    about_text = (
        "ℹ️ *О боте* ℹ️\n\n"
        "English Learning Bot — это интерактивный помощник для изучения английских слов, который помогает вам:\n\n"
        
        "• Учить новые слова каждый день в удобном темпе\n"
        "• Проходить тесты для закрепления знаний\n"
        "• Отслеживать свой прогресс\n"
        "• Повторять выученные слова для лучшего запоминания\n\n"
        
        "*Как работает обучение:*\n\n"
        
        "1. Бот отправляет вам уведомления со словами дня в течение дня\n"
        "2. Вы проходите квиз, чтобы проверить свои знания\n"
        "3. Правильно отвеченные слова добавляются в ваш словарь\n"
        "4. Невыученные слова повторяются на следующий день\n"
        "5. Когда вы выучили все слова в наборе, бот переходит в режим повторения\n\n"
        
        "Чтобы начать обучение, настройте свой уровень в разделе Настройки и используйте раздел Слова дня."
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
    Объясняет основные разделы бота и их функции.
    """
    commands_text = (
        "🔍 *Основные разделы бота* 🔍\n\n"
        
        "*📌 Слова дня*\n"
        "Показывает слова, которые вам нужно выучить сегодня. Эти же слова приходят в уведомлениях в течение дня. "
        "Количество слов и частоту повторений можно настроить в Настройках.\n\n"
        
        "*🎯 Квиз*\n"
        "Тест по словам дня. При правильном ответе слово добавляется в ваш словарь. "
        "Слова, которые вы не выучили, перейдут в слова дня на следующий день.\n\n"
        
        "*📖 Обучение*\n"
        "Дополнительные функции: тест по словам из вашего словаря и режим заучивания "
        "случайных слов из выбранного набора.\n\n"
        
        "*📚 Мой словарь*\n"
        "Здесь хранятся все выученные слова (слова, на которые вы правильно ответили в квизе). "
        "При смене набора слов ваш словарь очищается.\n\n"
        
        "*⚙️ Настройки*\n"
        "Настройте свой уровень, ежедневное количество слов, частоту повторений, часовой пояс "
        "и выберите набор слов для изучения."
    )
    
    await callback.message.edit_text(
        commands_text,
        parse_mode="Markdown",
        reply_markup=help_menu_keyboard()
    )
    await callback.answer()

async def process_help_tips_callback(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик кнопки "Советы по обучению" из меню помощи.
    Предоставляет советы для эффективного изучения слов.
    """
    tips_text = (
        "💡 *Советы по эффективному обучению* 💡\n\n"
        
        "• *Ежедневная практика*: Проверяйте уведомления и проходите квизы каждый день\n\n"
        
        "• *Оптимальная нагрузка*: Рекомендуемое количество новых слов в день — 5-10, "
        "чтобы избежать перегрузки и забывания\n\n"
        
        "• *Повторение*: Установите 3-5 повторений для лучшего запоминания\n\n"
        
        "• *Регулярные тесты*: Используйте раздел \"Тест по словарю\" для проверки ранее выученных слов\n\n"
        
        "• *Постепенное увеличение*: Начните с небольшого количества слов, "
        "постепенно увеличивая их число по мере привыкания\n\n"
        
        "• *Последовательность уровней*: Рекомендуется изучать наборы слов последовательно, от A1 до более высоких уровней\n\n"
        
        "• *Статистика*: Регулярно проверяйте свой прогресс в разделе \"Мой профиль\" в настройках"
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
    Предоставляет контактную информацию для связи с разработчиками.
    """
    feedback_text = (
        "✉️ *Обратная связь* ✉️\n\n"
        "Если у вас возникли вопросы, предложения или вы обнаружили ошибку:\n\n"
        
        "• Напишите в Telegram: @username\n"
        "• Email: support@example.com\n\n"
        
        "Мы ценим ваше мнение и стараемся сделать бота лучше!\n\n"
        
        "Помните, что бот находится в активной разработке, "
        "и мы регулярно добавляем новые функции и улучшения."
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