# handlers/words.py
from aiogram import types, Dispatcher, Bot
from database import crud
from keyboards.submenus import words_day_keyboard
from utils.helpers import get_daily_words_for_user
from config import REMINDER_START, DURATION_HOURS
from zoneinfo import ZoneInfo
from datetime import datetime

async def send_words_day_schedule(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик кнопки "Слова дня".
    Возвращает сохранённый набор слов для сегодняшнего дня с временными метками,
    вычисленными с учётом часового пояса пользователя.
    """
    chat_id = callback.from_user.id
    user = crud.get_user(chat_id)
    if not user:
        await bot.send_message(chat_id, "Профиль не найден. Пожалуйста, используйте /start.")
        return
    result = get_daily_words_for_user(chat_id, user[1], user[2], user[3],
                                       first_time=REMINDER_START, duration_hours=DURATION_HOURS)
    if result is None:
        await bot.send_message(chat_id, f"⚠️ Нет слов для уровня {user[1]}.")
        return
    messages, times = result
    total_notifications = user[2] * user[3]
    text = "📌 Сегодня вам будут отправлены следующие слова:\n\n"
    for i in range(total_notifications):
        t = times[i]
        msg = messages[i] if messages[i] else "(нет слов)"
        text += f"⏰ {t}:\n{msg}\n\n"
    text += "Нажмите кнопку ниже для возврата в главное меню."
    await bot.send_message(chat_id, text, reply_markup=words_day_keyboard())
    await callback.answer()

def register_words_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(
        lambda c: send_words_day_schedule(c, bot),
        lambda c: c.data == "menu:words_day"
    )
