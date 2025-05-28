# utils/subscription_helpers.py
import logging
from datetime import datetime
from pathlib import Path
from typing import List

from config import LEVELS_DIR, FREE_SETS
from database import crud

logger = logging.getLogger(__name__)

def get_available_sets_for_user(chat_id: int, level: str) -> List[str]:
    """
    Возвращает список доступных наборов для пользователя в зависимости от подписки.
    
    Args:
        chat_id: ID пользователя
        level: Уровень пользователя (A1, A2, B1, B2, C1, C2)
        
    Returns:
        Список доступных наборов
    """
    try:
        level_dir = Path(LEVELS_DIR) / level
        if not level_dir.exists():
            logger.warning(f"Level directory {level_dir} does not exist")
            return []
        
        # Получаем все наборы для уровня
        all_sets = [f.stem for f in level_dir.glob("*.txt")]
        
        # Проверяем статус подписки
        is_premium = crud.is_user_premium(chat_id)
        
        if is_premium:
            # Премиум пользователи имеют доступ ко всем наборам
            logger.debug(f"Premium user {chat_id} has access to all {len(all_sets)} sets for level {level}")
            return sorted(all_sets)
        else:
            # Бесплатные пользователи имеют доступ только к базовым наборам
            free_sets = FREE_SETS.get(level, [])
            available_sets = [s for s in all_sets if s in free_sets]
            logger.debug(f"Free user {chat_id} has access to {len(available_sets)} free sets for level {level}")
            return sorted(available_sets)
            
    except Exception as e:
        logger.error(f"Error getting available sets for user {chat_id}, level {level}: {e}")
        return []

def is_set_available_for_user(chat_id: int, set_name: str) -> bool:
    """
    Проверяет, доступен ли конкретный набор для пользователя.
    
    Args:
        chat_id: ID пользователя
        set_name: Название набора
        
    Returns:
        True если набор доступен, False если нет
    """
    try:
        # Определяем уровень из названия набора
        level = None
        for lvl in ["A1", "A2", "B1", "B2", "C1", "C2"]:
            if set_name.startswith(lvl):
                level = lvl
                break
                
        if not level:
            logger.warning(f"Could not determine level for set {set_name}")
            return False
            
        available_sets = get_available_sets_for_user(chat_id, level)
        is_available = set_name in available_sets
        
        logger.debug(f"Set {set_name} is {'available' if is_available else 'not available'} for user {chat_id}")
        return is_available
        
    except Exception as e:
        logger.error(f"Error checking set availability for user {chat_id}, set {set_name}: {e}")
        return False

def get_premium_sets_for_level(level: str) -> List[str]:
    """
    Возвращает список премиум наборов для указанного уровня.
    
    Args:
        level: Уровень (A1, A2, B1, B2, C1, C2)
        
    Returns:
        Список премиум наборов
    """
    try:
        level_dir = Path(LEVELS_DIR) / level
        if not level_dir.exists():
            return []
            
        all_sets = [f.stem for f in level_dir.glob("*.txt")]
        free_sets = FREE_SETS.get(level, [])
        premium_sets = [s for s in all_sets if s not in free_sets]
        
        logger.debug(f"Found {len(premium_sets)} premium sets for level {level}")
        return sorted(premium_sets)
        
    except Exception as e:
        logger.error(f"Error getting premium sets for level {level}: {e}")
        return []

def check_subscription_expiry(chat_id: int) -> dict:
    """
    Проверяет статус подписки и возвращает информацию о ней.
    
    Args:
        chat_id: ID пользователя
        
    Returns:
        Словарь с информацией о подписке
    """
    try:
        status, expires_at, payment_id = crud.get_user_subscription_status(chat_id)
        
        result = {
            "status": status,
            "is_premium": False,
            "expires_at": expires_at,
            "payment_id": payment_id,
            "days_left": 0,
            "expired": False
        }
        
        if status == 'premium' and expires_at:
            try:
                expiry_date = datetime.fromisoformat(expires_at)
                now = datetime.now()
                
                if now < expiry_date:
                    result["is_premium"] = True
                    result["days_left"] = (expiry_date - now).days
                else:
                    result["expired"] = True
                    # Обновляем статус в БД если подписка истекла
                    crud.update_user_subscription(chat_id, 'expired')
                    
            except ValueError as e:
                logger.error(f"Invalid expiry date format for user {chat_id}: {e}")
                
        return result
        
    except Exception as e:
        logger.error(f"Error checking subscription expiry for user {chat_id}: {e}")
        return {"status": "free", "is_premium": False, "expires_at": None, "payment_id": None, "days_left": 0, "expired": False}

def format_subscription_status(chat_id: int) -> str:
    """
    Форматирует информацию о статусе подписки для отображения пользователю.
    
    Args:
        chat_id: ID пользователя
        
    Returns:
        Отформатированная строка со статусом подписки
    """
    try:
        info = check_subscription_expiry(chat_id)
        
        if info["is_premium"]:
            days_left = info["days_left"]
            if days_left > 7:
                return f"💎 *Premium активен*\nОсталось дней: {days_left}"
            elif days_left > 0:
                return f"⚠️ *Premium истекает*\nОсталось дней: {days_left}"
            else:
                return f"⚠️ *Premium истекает сегодня*"
        elif info["expired"]:
            return "❌ *Premium истек*\nПродлите подписку для доступа ко всем наборам"
        else:
            return "🆓 *Бесплатный аккаунт*\nДоступны только базовые наборы"
            
    except Exception as e:
        logger.error(f"Error formatting subscription status for user {chat_id}: {e}")
        return "❓ *Статус неизвестен*"