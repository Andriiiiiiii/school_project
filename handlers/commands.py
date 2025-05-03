# handlers/commands.py
from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand, BotCommandScopeDefault
from utils.sticker_helper import get_welcome_sticker
from keyboards.reply_keyboards import get_main_menu_keyboard, get_remove_keyboard
from keyboards.main_menu import main_menu_keyboard  # Make sure this import is present
from database import crud
import logging

logger = logging.getLogger(__name__)

# Make sure this function is at the module level
async def set_commands(bot: Bot):
    """Установка команд бота для меню."""
    commands = [
        BotCommand(command="start", description="Перезапуск"),
        BotCommand(command="menu", description="Главное меню"),
        BotCommand(command="mode", description="Выбрать нейросеть"),
        BotCommand(command="profile", description="Профиль пользователя"),
        BotCommand(command="pay", description="Купить подписку"),
        BotCommand(command="reset", description="Сброс контекста"),
        BotCommand(command="help", description="Справка и помощь")
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())

async def cmd_start(message: types.Message, bot: Bot):
    """Обработчик команды /start."""
    chat_id = message.chat.id
    logger.info(f"Получена команда /start от chat_id: {chat_id}")
    
    try:
        # Import at the function level to avoid issues
        from keyboards.main_menu import main_menu_keyboard
        from keyboards.reply_keyboards import get_main_menu_keyboard
        
        # Проверяем, существует ли пользователь
        user = crud.get_user(chat_id)
        if not user:
            # Если нет - создаем запись
            crud.add_user(chat_id)
            logger.info(f"Добавлен новый пользователь с chat_id {chat_id}")
            
            # Устанавливаем базовый сет для A1
            from config import DEFAULT_SETS
            default_set = DEFAULT_SETS.get("A1")
            if default_set:
                try:
                    crud.update_user_chosen_set(chat_id, default_set)
                    # Обновляем кэш выбранных сетов
                    from handlers.settings import user_set_selection
                    user_set_selection[chat_id] = default_set
                    logger.info(f"Установлен базовый сет {default_set} для нового пользователя {chat_id}")
                except Exception as e:
                    logger.error(f"Ошибка при установке базового сета для нового пользователя {chat_id}: {e}")
            
            # Отправляем приветственный стикер для новых пользователей
            sticker_id = get_welcome_sticker()
            if sticker_id:
                await bot.send_sticker(chat_id, sticker_id)
        
        # Отправляем только одно приветственное сообщение с главным меню и reply keyboard
        await message.answer(
            "👋 *Добро пожаловать в English Learning Bot!*\n\n"
            "Этот бот поможет вам эффективно изучать английские слова:\n"
            "• Ежедневные наборы слов на ваш уровень\n"
            "• Квизы для закрепления и проверки знаний\n"
            "• Персональный словарь для отслеживания прогресса\n"
            "• Тестирование для определения вашего уровня\n"
            "• Система повторений для лучшего запоминания\n\n"
            "Выберите действие:",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        
        # Set the keyboard without sending additional message
        await bot.set_chat_menu_button(
            chat_id=chat_id,
            menu_button=types.MenuButtonCommands()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_start для chat_id {chat_id}: {e}")
        try:
            # Import here in case it was missed above
            from keyboards.main_menu import main_menu_keyboard
            
            # В случае ошибки отправляем только одно сообщение
            await message.answer(
                "👋 *Добро пожаловать в English Learning Bot!*\n\n"
                "Выберите действие:",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
            
        except Exception as e2:
            logger.error(f"Повторная ошибка в cmd_start для chat_id {chat_id}: {e2}")
            # Last resort - try to send something very basic
            await message.answer("Используйте команду /start для входа в главное меню.")

async def cmd_mode(message: types.Message):
    """Обработчик команды /mode."""
    await message.answer("Функция выбора нейросети в разработке.")

async def cmd_profile(message: types.Message):
    """Обработчик команды /profile."""
    from handlers.settings import process_settings_mysettings
    await process_settings_mysettings(message, message.bot)

async def cmd_pay(message: types.Message):
    """Обработчик команды /pay."""
    await message.answer("Функция покупки подписки в разработке.")

async def cmd_reset(message: types.Message):
    """Обработчик команды /reset."""
    await message.answer("Контекст сброшен.")

async def cmd_help(message: types.Message):
    """Обработчик команды /help."""
    from keyboards.submenus import help_menu_keyboard
    await message.answer(
        "*Справка по боту*\n\n"
        "English Learning Bot поможет вам изучать английские слова через:\n"
        "• Ежедневные наборы слов\n"
        "• Квизы для проверки знаний\n"
        "• Тесты для определения уровня\n"
        "• Персональный словарь\n\n"
        "Выберите раздел справки:",
        parse_mode="Markdown",
        reply_markup=help_menu_keyboard()
    )

async def cmd_menu(message: types.Message):
    """Показывает выдвигающееся меню команд."""
    await message.answer(
        "📋 Меню команд:",
        reply_markup=get_main_menu_keyboard()
    )

async def cmd_close_menu(message: types.Message):
    """Закрывает выдвигающееся меню."""
    from keyboards.main_menu import main_menu_keyboard
    await message.answer(
        "Меню закрыто. Используйте кнопки ниже или /menu для вызова меню команд:",
        reply_markup=main_menu_keyboard()
    )
def register_command_handlers(dp: Dispatcher, bot: Bot):
    """Регистрация обработчиков команд."""
    # Обработчик команды /start должен быть первым в списке и работать в любом состоянии бота
    dp.register_message_handler(lambda msg: cmd_start(msg, bot), commands=["start"], state="*")
    
    # Остальные команды
    dp.register_message_handler(cmd_mode, commands=["mode"])
    dp.register_message_handler(lambda msg: cmd_profile(msg, bot), commands=["profile"])
    dp.register_message_handler(cmd_pay, commands=["pay"])
    dp.register_message_handler(cmd_reset, commands=["reset"])
    dp.register_message_handler(cmd_help, commands=["help"])
    dp.register_message_handler(cmd_menu, commands=["menu"])
    dp.register_message_handler(cmd_close_menu, lambda msg: msg.text == "Закрыть меню")
    dp.register_message_handler(lambda msg: cmd_start(msg, bot), lambda msg: msg.text and "Перезапуск /start" in msg.text)