# debug_subscription.py
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_subscription(chat_id, level):
    """Отладка системы подписки для конкретного пользователя."""
    print(f"=== Отладка подписки для пользователя {chat_id}, уровень {level} ===")
    
    try:
        from database import crud
        from utils.subscription_helpers import (
            get_available_sets_for_user, 
            is_set_available_for_user,
            get_all_sets_for_level,
            get_premium_sets_for_level
        )
        from config import LEVELS_DIR, FREE_SETS
        
        # Проверяем статус подписки
        is_premium = crud.is_user_premium(chat_id)
        print(f"Премиум статус: {is_premium}")
        
        # Проверяем данные подписки
        status, expires_at, payment_id = crud.get_user_subscription_status(chat_id)
        print(f"Статус подписки: {status}")
        print(f"Истекает: {expires_at}")
        print(f"Payment ID: {payment_id}")
        
        # Проверяем наборы
        all_sets = get_all_sets_for_level(level)
        available_sets = get_available_sets_for_user(chat_id, level)
        premium_sets = get_premium_sets_for_level(level)
        free_sets = FREE_SETS.get(level, [])
        
        print(f"\nВсего наборов для уровня {level}: {len(all_sets)}")
        print(f"Доступных наборов: {len(available_sets)}")
        print(f"Премиум наборов: {len(premium_sets)}")
        print(f"Бесплатных наборов: {len(free_sets)}")
        
        print(f"\nБесплатные наборы: {free_sets}")
        print(f"Премиум наборы (первые 5): {premium_sets[:5]}")
        print(f"Доступные наборы (первые 5): {available_sets[:5]}")
        
        # Проверяем конкретные наборы
        test_sets = ["Advanced Academic Writing", "Global Economy & Finance", "C2 Basic 1"]
        for set_name in test_sets:
            if set_name in all_sets:
                is_available = is_set_available_for_user(chat_id, set_name)
                print(f"Набор '{set_name}': {'доступен' if is_available else 'заблокирован'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при отладке: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Замените на ваш chat_id и уровень
    chat_id = int(input("Введите ваш chat_id: "))
    level = input("Введите ваш уровень (A1, A2, B1, B2, C1, C2): ").upper()
    
    debug_subscription(chat_id, level)