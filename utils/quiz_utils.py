# utils/quiz_utils.py
"""
Shared utility functions for quiz and learning test functionality.
Extracts common logic to avoid duplication between quiz.py and learning.py.
"""

import random
import logging
from typing import Dict, List, Any, Tuple, Optional
from aiogram import Bot, types
from utils.visual_helpers import format_progress_bar
from utils.helpers import extract_english

logger = logging.getLogger(__name__)

def generate_quiz_options(correct_translation: str, 
                          all_translations: List[str], 
                          num_options: int = 4) -> Tuple[List[str], int]:
    """
    Generates quiz options including the correct answer and distractors.
    
    Args:
        correct_translation: The correct translation
        all_translations: Pool of all possible translations to use as distractors
        num_options: Number of options to generate (including correct answer)
        
    Returns:
        Tuple containing (list of options, index of correct option)
    """
    # Create a pool of distractors (excluding the correct answer)
    distractors_pool = [t for t in all_translations if t != correct_translation]
    
    # Add the correct translation
    options = [correct_translation]
    
    # Add distractors
    if len(distractors_pool) >= (num_options - 1):
        # If we have enough unique distractors, use them
        options.extend(random.sample(distractors_pool, num_options - 1))
    else:
        # If not enough distractors, use what we have (may include duplicates)
        if distractors_pool:
            options.extend(random.choices(distractors_pool, k=num_options - 1))
        else:
            # Fallback if no distractors available
            options.extend(["???"] * (num_options - 1))
    
    # Shuffle options
    random.shuffle(options)
    
    # Find index of correct answer
    correct_index = options.index(correct_translation)
    
    return options, correct_index

def create_quiz_keyboard(options: List[str], 
                         question_index: int, 
                         callback_prefix: str = "quiz") -> types.InlineKeyboardMarkup:
    """
    Creates a keyboard for quiz questions with options.
    
    Args:
        options: List of answer options
        question_index: Current question index
        callback_prefix: Prefix for callback data (quiz or learn)
        
    Returns:
        InlineKeyboardMarkup with options and control buttons
    """
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    # Add option buttons
    for i, option in enumerate(options):
        keyboard.add(types.InlineKeyboardButton(
            option, 
            callback_data=f"{callback_prefix}:answer:{question_index}:{i}"
        ))
    
    # Add control buttons
    keyboard.add(
        types.InlineKeyboardButton("🔙 Назад", callback_data=f"{callback_prefix}:back"),
        types.InlineKeyboardButton("⏹️ Стоп", callback_data=f"{callback_prefix}:stop")
    )
    
    return keyboard

async def send_quiz_question(chat_id: int, 
                            bot: Bot, 
                            state: Dict[str, Any], 
                            format_question_func, 
                            keyboard_func = None):
    """
    Sends a quiz question to the user.
    
    Args:
        chat_id: User's chat ID
        bot: Bot instance
        state: Quiz state dictionary
        format_question_func: Function to format the question text
        keyboard_func: Optional custom keyboard function
    """
    try:
        if not state:
            return
        
        current_index = state["current_index"]
        questions = state["questions"]
        
        if current_index >= len(questions):
            return  # Signal to finish the quiz
        
        question = questions[current_index]
        
        # Format the question text
        formatted_question = format_question_func(
            current_index + 1,
            len(questions),
            question
        )
        
        # Create keyboard
        if keyboard_func:
            keyboard = keyboard_func(question["options"], current_index)
        else:
            keyboard = create_quiz_keyboard(
                question["options"],
                current_index,
                "quiz" if state.get("test_type") != "dictionary" else "learn"
            )
        
        await bot.send_message(
            chat_id, 
            formatted_question,
            parse_mode="Markdown", 
            reply_markup=keyboard
        )
        return True
    except Exception as e:
        logger.error(f"Error sending quiz question: {e}")
        await bot.send_message(
            chat_id, 
            "Произошла ошибка при отправке вопроса. Пожалуйста, попробуйте позже.",
            parse_mode="Markdown"
        )
        return False

def process_quiz_answer(answer_index: int, 
                        question_index: int, 
                        state: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Processes a user's answer to a quiz question.
    
    Args:
        answer_index: The index of the selected answer
        question_index: The index of the current question
        state: Quiz state dictionary
        
    Returns:
        Tuple of (is_correct, feedback_message)
    """
    if question_index != state["current_index"]:
        return False, "Неверная последовательность вопросов."
        
    question = state["questions"][question_index]
    is_correct = (answer_index == question["correct_index"])
    
    if is_correct:
        state["correct"] += 1
        feedback = "Правильно!"
    else:
        feedback = f"Неправильно! Правильный ответ: {question['correct']}"
    
    # Advance to next question
    state["current_index"] += 1
    
    return is_correct, feedback

def format_poll_explanation(current_index: int, total: int, is_revision: bool = False) -> str:
    """
    Форматирует пояснение для встроенного опроса Telegram.
    Новая функция.
    
    Args:
        current_index: Текущий индекс вопроса (с 1)
        total: Общее количество вопросов
        is_revision: Флаг режима повторения
    
    Returns:
        Строка с пояснением для опроса
    """
    header = "🔄 ПОВТОРЕНИЕ" if is_revision else "🎯 КВИЗ"
    return f"{header} | Вопрос {current_index}/{total}"

def clean_word_for_poll(word: str) -> str:
    """
    Очищает слово от дополнительных данных для опроса.
    Новая функция.
    
    Args:
        word: Исходное слово, возможно содержащее разделители и перевод
        
    Returns:
        Очищенное слово для отображения в опросе
    """
    clean_word = word
    for separator in [" - ", " – ", ": "]:
        if separator in clean_word:
            clean_word = clean_word.split(separator, 1)[0].strip()
            break
    return clean_word