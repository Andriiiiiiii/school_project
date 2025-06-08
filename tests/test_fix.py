# test_fix.py
import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_reset_logic():
    """Тестирует исправленную логику сброса."""
    try:
        from database import crud
        from services.scheduler import process_daily_reset
        
        test_id = 888888
        
        # Создаем тестового пользователя
        try:
            crud.add_user(test_id)
        except:
            pass
        
        print("🧪 Тестирование исправленной логики сброса...")
        
        # Тест 1: Устанавливаем streak на позавчерашнюю дату
        day_before_yesterday = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        crud.update_user_streak(test_id, 5, day_before_yesterday)
        
        print(f"📅 Установлен streak=5 на дату {day_before_yesterday} (позавчера)")
        
        # Симулируем полуночный сброс
        process_daily_reset(test_id)
        
        # Проверяем результат
        new_streak, new_date = crud.get_user_streak(test_id)
        print(f"🌅 После полуночного сброса: streak={new_streak}, дата={new_date}")
        
        if new_streak == 0:
            print("✅ Сброс streak работает корректно!")
            return True
        else:
            print(f"❌ Streak не сбросился! Ожидалось 0, получено {new_streak}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_reset_logic()