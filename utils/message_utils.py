import logging
from typing import Optional, Union
from aiogram import types
from aiogram.types import InlineKeyboardMarkup

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4096
SAFE_MESSAGE_LENGTH = 4000  # Оставляем запас


async def safe_send_message(
    chat_id: int,
    text: str,
    bot,
    parse_mode: str = "Markdown",
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    disable_notification: bool = False
) -> types.Message:
    """
    Безопасно отправляет сообщение, автоматически обрезая его при необходимости.
    
    Args:
        chat_id: ID чата для отправки
        text: Текст сообщения
        bot: Экземпляр бота
        parse_mode: Режим парсинга (по умолчанию Markdown)
        reply_markup: Клавиатура для сообщения
        disable_notification: Отключить уведомление
        
    Returns:
        Отправленное сообщение
    """
    if len(text) <= SAFE_MESSAGE_LENGTH:
        return await bot.send_message(
            chat_id,
            text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            disable_notification=disable_notification
        )
    
    # Обрезаем сообщение
    truncated_text = text[:SAFE_MESSAGE_LENGTH - 50]
    truncated_text += "\n\n⚠️ *Сообщение обрезано из-за ограничений Telegram*"
    
    logger.warning(f"Message truncated: original length {len(text)}, truncated to {len(truncated_text)}")
    
    return await bot.send_message(
        chat_id,
        truncated_text,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
        disable_notification=disable_notification
    )


async def safe_edit_message(
    message: Union[types.Message, types.CallbackQuery],
    text: str,
    parse_mode: str = "Markdown",
    reply_markup: Optional[InlineKeyboardMarkup] = None
) -> types.Message:
    """
    Безопасно редактирует сообщение, автоматически обрезая его при необходимости.
    
    Args:
        message: Сообщение для редактирования или CallbackQuery
        text: Новый текст сообщения
        parse_mode: Режим парсинга (по умолчанию Markdown)
        reply_markup: Клавиатура для сообщения
        
    Returns:
        Отредактированное сообщение
    """
    # Получаем объект сообщения
    if isinstance(message, types.CallbackQuery):
        message_obj = message.message
    else:
        message_obj = message
    
    if len(text) <= SAFE_MESSAGE_LENGTH:
        return await message_obj.edit_text(
            text,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )
    
    # Обрезаем сообщение
    truncated_text = text[:SAFE_MESSAGE_LENGTH - 50]
    truncated_text += "\n\n⚠️ *Сообщение обрезано из-за ограничений Telegram*"
    
    logger.warning(f"Message truncated on edit: original length {len(text)}, truncated to {len(truncated_text)}")
    
    return await message_obj.edit_text(
        truncated_text,
        parse_mode=parse_mode,
        reply_markup=reply_markup
    )


def check_message_length(text: str) -> tuple[bool, Optional[str]]:
    """
    Проверяет длину сообщения и возвращает информацию о необходимости обрезки.
    
    Args:
        text: Текст для проверки
        
    Returns:
        Tuple (нужна_ли_обрезка, сообщение_об_ошибке)
    """
    if len(text) <= SAFE_MESSAGE_LENGTH:
        return False, None
    
    excess = len(text) - SAFE_MESSAGE_LENGTH
    return True, f"Сообщение превышает лимит на {excess} символов"