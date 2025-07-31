# handlers/referrals.py
import logging
from functools import partial
from urllib.parse import quote

from aiogram import Bot, Dispatcher, types

from config import BOT_TOKEN
from database import crud
from keyboards.referrals import referral_menu_keyboard

logger = logging.getLogger(__name__)

async def get_bot_username(bot: Bot):
    """Получает username бота через API."""
    try:
        bot_info = await bot.get_me()
        return bot_info.username or "AllHabitsTrackerBot"  # fallback если username None
    except Exception as e:
        logger.error(f"Error getting bot username: {e}")
        return "AllHabitsTrackerBot"  # Замените на реальное имя вашего бота


async def show_referral_menu(callback: types.CallbackQuery, bot: Bot):
    """Показывает главное меню реферальной системы."""
    chat_id = callback.from_user.id
    
    # Получаем данные пользователя
    referral_code = crud.set_user_referral_code(chat_id)
    referrals_count = crud.count_user_referrals(chat_id)
    
    # Создаем реферальную ссылку
    bot_username = await get_bot_username(bot)
    referral_link = f"https://t.me/{bot_username}?start=ref_{referral_code}"
    
    text = (
        "👥 *Пригласи друзей*\n\n"
        "🎁 *За каждых 5 друзей получай месяц Premium!*\n\n"
        f"👥 Приглашено друзей: *{referrals_count}/5*\n"
        f"🔗 Ваша реферальная ссылка:\n`{referral_link}`\n\n"
        "📋 *Как это работает:*\n"
        "1. Поделитесь ссылкой с друзьями\n"
        "2. Друзья запускают бота по вашей ссылке\n"
        "3. За каждых 5 друзей получаете месяц Premium\n\n"
    )
    
    if referrals_count >= 5:
        completed_rewards = referrals_count // 5
        text += f"🎉 *Вы уже получили {completed_rewards} наград!*\n"
        next_reward_progress = referrals_count % 5
        if next_reward_progress > 0:
            text += f"📊 До следующей награды: {next_reward_progress}/5\n"
    else:
        text += f"📊 До первой награды: {referrals_count}/5\n"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",  # Используем обычный Markdown
        reply_markup=referral_menu_keyboard()
    )
    await callback.answer()

async def show_referral_history(callback: types.CallbackQuery, bot: Bot):
    """Показывает историю приглашенных друзей."""
    chat_id = callback.from_user.id
    referrals = crud.get_user_referrals(chat_id)
    
    if not referrals:
        text = "👥 *История приглашений*\n\nВы еще никого не пригласили."
    else:
        text = f"👥 *История приглашений*\n\nВсего друзей: *{len(referrals)}*\n\n"
        
        for i, (referred_id, created_at, _) in enumerate(referrals[:10], 1):
            try:
                date = created_at.split('T')[0] if 'T' in created_at else created_at[:10]
                text += f"{i}. Друг #{referred_id} — {date}\n"
            except:
                text += f"{i}. Друг #{referred_id}\n"
        
        if len(referrals) > 10:
            text += f"\n...и еще {len(referrals) - 10} друзей"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",  # Используем обычный Markdown
        reply_markup=referral_menu_keyboard()
    )
    await callback.answer()

async def share_referral_link(callback: types.CallbackQuery, bot: Bot):
    """Создает сообщение для удобного копирования реферальной ссылки."""
    chat_id = callback.from_user.id
    referral_code = crud.set_user_referral_code(chat_id)
    bot_username = await get_bot_username(bot)
    referral_link = f"https://t.me/{bot_username}?start=ref_{referral_code}"
    
    share_text = (
        "🎓 Изучай английский с удовольствием!\n\n"
        "Попробуй крутого бота для изучения английского языка:\n"
        "• Ежедневные слова\n"
        "• Интерактивные тесты\n"
        "• Персональный словарь\n"
        "• Различные уровни сложности\n\n"
        f"Попробуй здесь: {referral_link}"
    )
    
    message_text = f"📤 Готовое сообщение для друзей:\n\n{share_text}"
    
    await bot.send_message(
        chat_id,
        message_text,
        parse_mode=None  # Убираем Markdown парсинг
    )
    await callback.answer("Сообщение отправлено! Скопируйте и поделитесь с друзьями.")

def register_referral_handlers(dp: Dispatcher, bot: Bot):
    """Регистрирует обработчики реферальной системы."""
    
    dp.register_callback_query_handler(
        partial(show_referral_menu, bot=bot),
        lambda c: c.data == "menu:referrals"
    )
    
    dp.register_callback_query_handler(
        partial(show_referral_history, bot=bot),
        lambda c: c.data == "referrals:history"
    )
    
    dp.register_callback_query_handler(
        partial(share_referral_link, bot=bot),
        lambda c: c.data == "referrals:share"
    )