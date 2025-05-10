# handlers/commands.py
from __future__ import annotations

import logging
from functools import partial

from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand

from config import DEFAULT_SETS
from database import crud
from keyboards.main_menu import main_menu_keyboard
from keyboards.reply_keyboards import get_main_menu_keyboard
from utils.sticker_helper import get_welcome_sticker

logger = logging.getLogger(__name__)

# ─────────────────────────── КОМАНДЫ БОТА (список) ─────────────────────────
BOT_COMMANDS: list[BotCommand] = [
    BotCommand("start", "Перезапуск"),
    BotCommand("menu", "Главное меню"),
    BotCommand("mode", "Выбрать нейросеть"),
    BotCommand("profile", "Профиль пользователя"),
    BotCommand("pay", "Купить подписку"),
    BotCommand("reset", "Сброс контекста"),
    BotCommand("help", "Справка и помощь"),
]


async def set_commands(bot: Bot) -> None:
    """Регистрация /команд в клиентском меню."""
    await bot.set_my_commands(BOT_COMMANDS)


# ─────────────────────────────── /START ────────────────────────────────────
async def cmd_start(message: types.Message, bot: Bot) -> None:
    chat_id = message.chat.id
    logger.info("Команда /start от chat_id=%s", chat_id)

    try:
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

            sticker_id = get_welcome_sticker()
            if sticker_id:
                await bot.send_sticker(chat_id, sticker_id)

        # ─── приветственное сообщение + главное меню ───────────────────────
        await message.answer(
            "👋 *Добро пожаловать в English Learning Bot!*\n\n"
            "• Ежедневные наборы слов\n"
            "• Квизы для закрепления\n"
            "• Персональный словарь\n"
            "• Тестирование уровня\n\n"
            "Выберите действие:",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )

        # кнопка «Команды» в меню чата
        await bot.set_chat_menu_button(chat_id, types.MenuButtonCommands())

    except Exception as exc:  # fallback
        logger.exception("Ошибка в cmd_start: %s", exc)
        await message.answer(
            "👋 *Добро пожаловать!*\n\nВыберите действие:",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )


# ──────────────────────── ОСТАЛЬНЫЕ КОМАНДЫ ────────────────────────────────
async def cmd_mode(message: types.Message) -> None:
    await message.answer("Функция выбора нейросети в разработке.")


async def cmd_profile(message: types.Message) -> None:
    from handlers.settings import process_settings_mysettings

    await process_settings_mysettings(message, message.bot)


async def cmd_pay(message: types.Message) -> None:
    await message.answer("Функция покупки подписки в разработке.")


async def cmd_reset(message: types.Message) -> None:
    await message.answer("Контекст сброшен.")


async def cmd_help(message: types.Message) -> None:
    from keyboards.submenus import help_menu_keyboard

    await message.answer(
        "*Справка по боту*\n\n"
        "English Learning Bot помогает изучать английский язык через:\n"
        "• Ежедневные подборки слов\n"
        "• Квизы и тесты\n"
        "• Персональный словарь\n\n"
        "Выберите раздел справки:",
        parse_mode="Markdown",
        reply_markup=help_menu_keyboard(),
    )


async def cmd_menu(message: types.Message) -> None:
    await message.answer("📋 Меню команд:", reply_markup=get_main_menu_keyboard())


async def cmd_close_menu(message: types.Message) -> None:
    await message.answer(
        "Меню закрыто. Используйте кнопки ниже или /menu для вызова меню команд:",
        reply_markup=main_menu_keyboard(),
    )


# ───────────────────────── РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ──────────────────────────
def register_command_handlers(dp: Dispatcher, bot: Bot) -> None:
    """Подключает все вышеописанные команды к диспетчеру."""
    dp.register_message_handler(partial(cmd_start, bot=bot), commands="start", state="*")

    dp.register_message_handler(cmd_mode, commands="mode")
    dp.register_message_handler(cmd_profile, commands="profile")
    dp.register_message_handler(cmd_pay, commands="pay")
    dp.register_message_handler(cmd_reset, commands="reset")
    dp.register_message_handler(cmd_help, commands="help")
    dp.register_message_handler(cmd_menu, commands="menu")

    # кнопка «Закрыть меню» из reply-keyboard
    dp.register_message_handler(cmd_close_menu, lambda m: m.text == "Закрыть меню")

    # текстовая фраза «Перезапуск /start» (если используется в интерфейсе)
    dp.register_message_handler(
        partial(cmd_start, bot=bot),
        lambda m: m.text and "Перезапуск /start" in m.text,
    )
