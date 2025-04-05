# utils/sticker_helper.py
import random
import logging
from typing import List

logger = logging.getLogger(__name__)

# ID стикеров для поздравлений (нужно заменить на настоящие ID)
# Эти примеры нужно будет заменить на реальные стикеры из Telegram
CONGRATULATION_STICKERS = [
    "CAACAgIAAxkBAAEKX2RlB3TN7AAB3o7Dh4QXsaU6SWHccpQAAjcHAAJlhUhLOh2LB8jQBDswBA",  # Аплодисменты
    "CAACAgIAAxkBAAEKX2ZlB3VnXKiJ7AABaRpSmMhlg3JFQmQAAkIHAAL2U-hLNLtFY_Tf0GUwBA",  # Победа
    "CAACAgIAAxkBAAEKX2hlB3V8Tit78f3MF-Z20VkfUvl7KAACbgUAAvLm-UtcQxCPuiDzijAE",    # Отлично
    "CAACAgIAAxkBAAEKX2plB3WNvnIuI7Cp5fJGW2vkBQgxwwACaQQAAvoLtgz5uFAl45Q-EDAE"     # Молодец
]

# ID стикеров для других ситуаций
LEVEL_UP_STICKERS = [
    "CAACAgIAAxkBAAEKX2xlB3WqKpxGw4juDrO-9JYlnwMBBgACSAYAApb6mEtdGC_QpHZMfjAE",  # Новый уровень
    "CAACAgIAAxkBAAEKX25lB3W7PgabrU-agWQny-gGQsT0cgACTQYAAgw7mEu8TCGVzn1dYDAE"   # Повышение
]

WELCOME_STICKERS = [
    "CAACAgIAAxkBAAEKX3BlB3XNCQlI9RgqQFJ_OvCjFd6FsgACSQkAAqHemEvHxS8oKuKavjAE",  # Приветствие
    "CAACAgIAAxkBAAEKX3JlB3Xh9wnyCQtajdSqxu-2wQk3nwACTQkAAkgGmUtxGVdQyBbR_DAE"   # Рукопожатие
]

def get_random_sticker(sticker_list: List[str]) -> str:
    """Возвращает случайный стикер из списка."""
    if not sticker_list:
        logger.warning("Пустой список стикеров")
        return None
    return random.choice(sticker_list)

def get_congratulation_sticker(score_percentage: float = None) -> str:
    """
    Возвращает поздравительный стикер. 
    Можно выбрать в зависимости от процента правильных ответов.
    """
    return get_random_sticker(CONGRATULATION_STICKERS)

def get_level_up_sticker() -> str:
    """Возвращает стикер для повышения уровня."""
    return get_random_sticker(LEVEL_UP_STICKERS)

def get_welcome_sticker() -> str:
    """Возвращает приветственный стикер."""
    return get_random_sticker(WELCOME_STICKERS)