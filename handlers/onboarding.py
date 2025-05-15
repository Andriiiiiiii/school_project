# handlers/onboarding.py
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database import crud
from config import REMINDER_START, DURATION_HOURS, DEFAULT_SETS
from utils.helpers import get_daily_words_for_user, reset_daily_words_cache
from keyboards.main_menu import main_menu_keyboard
from keyboards.submenus import words_day_keyboard
from utils.visual_helpers import format_daily_words_message

# Настройка логирования
logger = logging.getLogger(__name__)

# Словарь для отслеживания состояния пользователя в процессе онбординга
# {chat_id: {"step": "level", "level": "A1", "words": 5}}
onboarding_states = {}

# Клавиатуры для разных шагов онбординга
def level_keyboard():
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("A1", callback_data="onboarding:level:A1"),
        InlineKeyboardButton("A2", callback_data="onboarding:level:A2"),
        InlineKeyboardButton("B1", callback_data="onboarding:level:B1")
    )
    kb.add(
        InlineKeyboardButton("B2", callback_data="onboarding:level:B2"),
        InlineKeyboardButton("C1", callback_data="onboarding:level:C1"),
        InlineKeyboardButton("C2", callback_data="onboarding:level:C2")
    )
    return kb

def words_per_day_keyboard():
    kb = InlineKeyboardMarkup(row_width=5)
    kb.add(
        InlineKeyboardButton("3", callback_data="onboarding:words:3"),
        InlineKeyboardButton("5", callback_data="onboarding:words:5"),
        InlineKeyboardButton("7", callback_data="onboarding:words:7"),
        InlineKeyboardButton("10", callback_data="onboarding:words:10"),
        InlineKeyboardButton("15", callback_data="onboarding:words:15")
    )
    return kb

def repetitions_keyboard():
    kb = InlineKeyboardMarkup(row_width=5)
    kb.add(
        InlineKeyboardButton("1", callback_data="onboarding:reps:1"),
        InlineKeyboardButton("2", callback_data="onboarding:reps:2"),
        InlineKeyboardButton("3", callback_data="onboarding:reps:3"),
        InlineKeyboardButton("4", callback_data="onboarding:reps:4"),
        InlineKeyboardButton("5", callback_data="onboarding:reps:5")
    )
    return kb

# Функция начала онбординга (вызывается из cmd_start)
async def start_onboarding(message, bot):
    chat_id = message.chat.id
    
    # Инициализируем состояние онбординга
    onboarding_states[chat_id] = {"step": "level"}
    
    await message.answer(
        "Добро пожаловать в бот для изучения английского! Давайте настроим ваш профиль за 3 простых шага:\n\n"
        "Сначала, какой у вас уровень английского?",
        reply_markup=level_keyboard()
    )

# Обработчик процесса онбординга
async def process_onboarding(callback: types.CallbackQuery, bot: Bot):
    chat_id = callback.from_user.id
    
    # Проверяем, есть ли пользователь в процессе онбординга
    if chat_id not in onboarding_states:
        logger.warning(f"Пользователь {chat_id} не в процессе онбординга")
        await callback.answer("Произошла ошибка. Пожалуйста, начните заново с /start.")
        return
    
    state = onboarding_states[chat_id]
    data_parts = callback.data.split(":")
    
    if len(data_parts) != 3:
        logger.warning(f"Неправильный формат callback_data: {callback.data}")
        await callback.answer("Произошла ошибка. Пожалуйста, начните заново с /start.")
        return
    
    action_type = data_parts[1]  # level, words, reps
    value = data_parts[2]
    
    # Обработка выбора уровня
    if action_type == "level" and state["step"] == "level":
        level = value
        state["level"] = level
        state["step"] = "words"
        
        # Сохраняем уровень в БД
        crud.update_user_level(chat_id, level)
        
        # Также устанавливаем набор слов по умолчанию для выбранного уровня
        default_set = DEFAULT_SETS.get(level)
        if default_set:
            crud.update_user_chosen_set(chat_id, default_set)
            # Обновляем кэш выбранных сетов, если он используется
            try:
                from handlers.settings import user_set_selection
                user_set_selection[chat_id] = default_set
            except (ImportError, AttributeError):
                pass
        
        await callback.message.edit_text(
            f"Отлично! Вы выбрали уровень {level}.\n\n"
            "Сколько новых слов вы хотели бы изучать ежедневно? (Рекомендуется 5-10)",
            reply_markup=words_per_day_keyboard()
        )
    
    # Обработка выбора количества слов
    elif action_type == "words" and state["step"] == "words":
        words = int(value)
        state["words"] = words
        state["step"] = "reps"
        
        # Сохраняем количество слов в БД
        crud.update_user_words_per_day(chat_id, words)
        
        await callback.message.edit_text(
            f"Вы будете изучать {words} новых слов в день.\n\n"
            "Сколько раз вы хотели бы видеть каждое слово в течение дня?",
            reply_markup=repetitions_keyboard()
        )
    
    # Обработка выбора количества повторений
    elif action_type == "reps" and state["step"] == "reps":
        reps = int(value)
        state["reps"] = reps
        state["step"] = "finished"
        
        # Сохраняем количество повторений в БД
        crud.update_user_notifications(chat_id, reps)
        
        # Получаем данные из состояния
        level = state["level"]
        words = state["words"]
        
        # Сбрасываем кэш слов дня
        reset_daily_words_cache(chat_id)
        
        # Отправляем завершающее сообщение
        await callback.message.edit_text(
            f"Отлично! Всё готово для начала обучения.\n\n"
            f"Ваши настройки:\n"
            f"• Уровень: {level}\n"
            f"• Слов в день: {words}\n"
            f"• Повторений: {reps}\n\n"
            "Загружаю ваши первые слова на сегодня..."
        )
        
        # Удаляем пользователя из словаря состояний онбординга
        onboarding_states.pop(chat_id, None)
        
        # Показываем первые слова
        await send_first_words(chat_id, level, words, reps, bot)
    
    else:
        logger.warning(f"Несоответствие шага и типа действия: {state['step']} != {action_type}")
        await callback.answer("Произошла ошибка. Пожалуйста, начните заново с /start.")
    
    await callback.answer()

# Функция для отправки первых слов
async def send_first_words(chat_id, level, words_count, repetitions, bot):
    # Получаем первые слова дня
    try:
        result = get_daily_words_for_user(
            chat_id, level, words_count, repetitions,
            first_time=REMINDER_START, duration_hours=DURATION_HOURS,
            force_reset=True
        )
        
        if result:
            messages, times = result
            
            # Форматируем сообщение с первыми словами
            words_message = format_daily_words_message(messages, times)
            
            # Отправляем сообщение с первыми словами
            await bot.send_message(
                chat_id,
                words_message,
                parse_mode="Markdown",
                reply_markup=words_day_keyboard()
            )
            
            # Объясняем функцию квиза
            await bot.send_message(
                chat_id,
                "Каждый день в течение дня вам приходят новые *Слова дня* из *Набора слов* вашего уровня сложности. \n \n"
                "Для закрепления *Слов дня* рекомендую пройти *Тест дня*.\n\n"
                "Правильно отвеченные слова будут добавлены в ваш личный *словарь*.\n\n"
                "Вы всегда можете пройти квиз, нажав на кнопку *Тест дня* в главном меню.",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        else:
            # Если не удалось получить слова, показываем обычное меню
            await bot.send_message(
                chat_id,
                "Не удалось загрузить слова. Пожалуйста, попробуйте позже или настройте параметры в разделе Настройки.",
                reply_markup=main_menu_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка при отправке первых слов: {e}")
        # В случае ошибки показываем главное меню
        await bot.send_message(
            chat_id,
            "Произошла ошибка при загрузке слов. Пожалуйста, проверьте настройки или попробуйте позже.",
            reply_markup=main_menu_keyboard()
        )

# Функция регистрации обработчиков
def register_onboarding_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(
        lambda c: process_onboarding(c, bot),
        lambda c: c.data.startswith("onboarding:"),
    )