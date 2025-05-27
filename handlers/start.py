# handlers/start.py
import logging
from aiogram import types
from keyboards.main_menu import main_menu_keyboard
from database import crud

logger = logging.getLogger(__name__)

# Обновленная функция cmd_start из handlers/commands.py

async def cmd_start(message: types.Message, bot: Bot) -> None:
    chat_id = message.chat.id
    logger.info("Команда /start от chat_id=%s", chat_id)

    try:
        # Явно устанавливаем кнопку меню команд для этого конкретного чата
        await bot.set_chat_menu_button(chat_id=chat_id, menu_button=MenuButtonCommands())
        
        # ─── регистрация нового пользователя ───────────────────────────────
        if not crud.get_user(chat_id):
            crud.add_user(chat_id)
            logger.info("Создан новый пользователь %s", chat_id)

            default_set = DEFAULT_SETS.get("A1")
            if default_set:
                crud.update_user_chosen_set(chat_id, default_set)
                from handlers.settings import user_set_selection

                user_set_selection[chat_id] = default_set
                logger.info("Базовый сет %s назначен пользователю %s", default_set, chat_id)

            # Начинаем процесс онбординга для нового пользователя
            from handlers.onboarding import start_onboarding
            await start_onboarding(message, bot)
            return

        # ─── приветственное сообщение + главное меню ───────────────────────
        await message.answer(
            "👋 *Добро пожаловать обратно!*\n\n"
            "🎯 *Как работает бот:*\n"
            "1️⃣ Каждый день вы получаете новые слова из выбранной темы\n"
            "2️⃣ Слова приходят в течение дня как уведомления\n" 
            "3️⃣ Проходите тест дня → выученные слова сохраняются в словарь\n"
            "4️⃣ Невыученные слова повторятся завтра\n\n"
            "📚 *Набор слов* — это готовая тема с английскими словами (например: «Базовый A1», «Путешествия B1»)\n\n"
            "Готовы продолжить изучение?",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )

    except Exception as exc:  # fallback
        logger.exception("Ошибка в cmd_start: %s", exc)
        await message.answer(
            "👋 *Добро пожаловать!*\n\nВыберите действие:",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )