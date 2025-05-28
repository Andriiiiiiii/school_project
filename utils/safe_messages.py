# utils/safe_message.py

import logging
from aiogram import types, Bot
from aiogram.utils.exceptions import MessageNotModified, BadRequest, TelegramAPIError
from typing import Optional, Union

logger = logging.getLogger(__name__)

async def safe_edit_message(
    callback: types.CallbackQuery,
    text: str,
    parse_mode: str = "Markdown",
    reply_markup: Optional[types.InlineKeyboardMarkup] = None,
    bot: Optional[Bot] = None
) -> bool:
    """
    Безопасно редактирует сообщение с обработкой исключения MessageNotModified.
    
    Args:
        callback: CallbackQuery объект
        text: Новый текст сообщения
        parse_mode: Режим парсинга (по умолчанию Markdown)
        reply_markup: Клавиатура (опционально)
        bot: Экземпляр бота (для fallback, опционально)
        
    Returns:
        bool: True если сообщение было отредактировано или отправлено, False если произошла ошибка
    """
    try:
        await callback.message.edit_text(
            text,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )
        logger.debug(f"Message successfully edited for user {callback.from_user.id}")
        return True
    except MessageNotModified:
        logger.debug(f"Message not modified for user {callback.from_user.id} - content is identical")
        return True  # Считаем успешным, так как содержимое уже корректное
    except BadRequest as e:
        logger.warning(f"Bad request when editing message for user {callback.from_user.id}: {e}")
        # Пытаемся отправить новое сообщение как fallback
        if bot:
            try:
                await bot.send_message(
                    callback.from_user.id,
                    text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup
                )
                logger.info(f"Sent fallback message for user {callback.from_user.id}")
                return True
            except Exception as fallback_error:
                logger.error(f"Fallback message send failed for user {callback.from_user.id}: {fallback_error}")
        return False
    except TelegramAPIError as e:
        logger.error(f"Telegram API error when editing message for user {callback.from_user.id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error editing message for user {callback.from_user.id}: {e}")
        return False

async def safe_edit_reply_markup(
    callback: types.CallbackQuery,
    reply_markup: Optional[types.InlineKeyboardMarkup] = None
) -> bool:
    """
    Безопасно редактирует только клавиатуру сообщения.
    
    Args:
        callback: CallbackQuery объект
        reply_markup: Новая клавиатура
        
    Returns:
        bool: True если клавиатура была отредактирована, False если произошла ошибка
    """
    try:
        await callback.message.edit_reply_markup(reply_markup=reply_markup)
        logger.debug(f"Reply markup successfully edited for user {callback.from_user.id}")
        return True
    except MessageNotModified:
        logger.debug(f"Reply markup not modified for user {callback.from_user.id} - identical")
        return True
    except Exception as e:
        logger.error(f"Error editing reply markup for user {callback.from_user.id}: {e}")
        return False

async def safe_answer_callback(
    callback: types.CallbackQuery, 
    text: str = None, 
    show_alert: bool = False,
    cache_time: int = None
) -> bool:
    """
    Безопасно отвечает на callback query с обработкой ошибок.
    
    Args:
        callback: CallbackQuery объект
        text: Текст для показа пользователю (опционально)
        show_alert: Показать как всплывающее окно
        cache_time: Время кэширования ответа в секундах
        
    Returns:
        bool: True если ответ был отправлен, False если произошла ошибка
    """
    try:
        await callback.answer(text=text, show_alert=show_alert, cache_time=cache_time)
        return True
    except Exception as e:
        logger.error(f"Error answering callback for user {callback.from_user.id}: {e}")
        return False

async def safe_send_message(
    bot: Bot,
    chat_id: Union[int, str],
    text: str,
    parse_mode: str = "Markdown",
    reply_markup: Optional[types.InlineKeyboardMarkup] = None,
    disable_notification: bool = False,
    disable_web_page_preview: bool = True
) -> Optional[types.Message]:
    """
    Безопасно отправляет сообщение с обработкой ошибок.
    
    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        text: Текст сообщения
        parse_mode: Режим парсинга
        reply_markup: Клавиатура (опционально)
        disable_notification: Отключить уведомление
        disable_web_page_preview: Отключить превью ссылок
        
    Returns:
        types.Message: Отправленное сообщение или None в случае ошибки
    """
    try:
        message = await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            disable_notification=disable_notification,
            disable_web_page_preview=disable_web_page_preview
        )
        logger.debug(f"Message successfully sent to chat {chat_id}")
        return message
    except BadRequest as e:
        logger.warning(f"Bad request when sending message to chat {chat_id}: {e}")
        return None
    except TelegramAPIError as e:
        logger.error(f"Telegram API error when sending message to chat {chat_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error sending message to chat {chat_id}: {e}")
        return None

async def safe_delete_message(
    bot: Bot,
    chat_id: Union[int, str],
    message_id: int
) -> bool:
    """
    Безопасно удаляет сообщение с обработкой ошибок.
    
    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        message_id: ID сообщения для удаления
        
    Returns:
        bool: True если сообщение было удалено, False если произошла ошибка
    """
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.debug(f"Message {message_id} successfully deleted from chat {chat_id}")
        return True
    except BadRequest as e:
        logger.warning(f"Bad request when deleting message {message_id} from chat {chat_id}: {e}")
        return False
    except TelegramAPIError as e:
        logger.error(f"Telegram API error when deleting message {message_id} from chat {chat_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting message {message_id} from chat {chat_id}: {e}")
        return False

# Декоратор для автоматической обработки MessageNotModified
def handle_message_not_modified(func):
    """
    Декоратор для автоматической обработки исключения MessageNotModified.
    
    Использование:
    @handle_message_not_modified
    async def some_handler(callback: types.CallbackQuery):
        await callback.message.edit_text("New text")
    """
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except MessageNotModified:
            logger.debug("Message not modified - ignoring")
            return True
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            raise
    return wrapper

# Пример использования в обработчиках:
"""
# Вариант 1: Использование функции напрямую
async def some_handler(callback: types.CallbackQuery, bot: Bot):
    success = await safe_edit_message(
        callback,
        "Новый текст сообщения",
        reply_markup=some_keyboard(),
        bot=bot
    )
    
    await safe_answer_callback(callback)

# Вариант 2: Использование декоратора
@handle_message_not_modified
async def another_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Новый текст",
        reply_markup=some_keyboard()
    )
    await callback.answer()
"""