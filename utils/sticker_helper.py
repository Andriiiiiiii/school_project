# utils/sticker_helper.py
import random
import logging
from typing import List

logger = logging.getLogger(__name__)

# ID стикеров для поздравлений (нужно заменить на настоящие ID)
CONGRATULATION_STICKERS = [
    "CAACAgIAAxkBAAEOGn9n8VgDNk-LiGKGtIFdoF-mcH7dFwACsUIAAuzowEncnUsSshcY4jYE",  # Аплодисменты
    "CAACAgIAAxkBAAEOGoNn8VhCLHSxD3n-LgLEb6EHE59psQACqCoAAkRtWUi50I6LZeu10TYE",  # Победа
    "CAACAgIAAxkBAAEOGodn8VhlbulYsIr_PMipimhuebHVwgACIDsAAo_yUEhLNqxeSlOWvDYE",    # Отлично
    "CAACAgIAAxkBAAEOGoln8Vh69Z4X9znkmJ1OerOdEkWZyAACbyoAAqAVWEjIcv-tVvXsRTYE"     # Молодец
]

# ID стикеров для других ситуаций
CLEAN_STICKERS = [
    "CAACAgIAAxkBAAEOGmJn8VSOHXIYi01pBkUEsCPEyTDC1AAC1ygAAtzp6Eg7WBFqJXABxjYE",  # Новый уровень
    "CAACAgIAAxkBAAEOGoVn8VhYr_JhwOAYBk-leBdZde9-FgACgzgAAvxWgEtjNWPp4shPgzYE"   # Повышение
]

WELCOME_STICKERS = [
    "CAACAgIAAxkBAAEOGmJn8VSOHXIYi01pBkUEsCPEyTDC1AAC1ygAAtzp6Eg7WBFqJXABxjYE",  # Приветствие
    "CAACAgIAAxkBAAEOGmJn8VSOHXIYi01pBkUEsCPEyTDC1AAC1ygAAtzp6Eg7WBFqJXABxjYE"   # Рукопожатие
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

def get_clean_sticker() -> str:
    """Возвращает стикер для повышения уровня."""
    return get_random_sticker(CLEAN_STICKERS)

def get_welcome_sticker() -> str:
    """Возвращает приветственный стикер."""
    return get_random_sticker(WELCOME_STICKERS)