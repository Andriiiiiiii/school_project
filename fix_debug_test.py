# fix_debug_test.py
import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_midnight_reset_with_reload():
    """Тестирует логику сброса с принудительной перезагрузкой модулей."""
    try:
        # ПРИНУДИТЕЛЬНАЯ ПЕРЕЗАГРУЗКА МОДУЛЕЙ
        import importlib
        
        # Удаляем модули из кэша
        modules_to_reload = [
            'services.scheduler',
            'database.crud',
            'utils.helpers'
        ]
        
        for module_name in modules_to_reload:
            if module_name in sys.modules:
                print(f"🔄 Перезагружаем модуль {module_name}")
                importlib.reload(sys.modules[module_name])
        
        # Теперь импортируем заново
        from database import crud
        from services.scheduler import process_daily_reset
        
        test_id = 555555
        
        # Создаем тестового пользователя
        try:
            crud.add_user(test_id)
        except:
            pass
        
        print("🧪 Тестирование ОБНОВЛЕННОЙ логики сброса...")
        
        # Тест 1: Устанавливаем streak на вчерашнюю дату
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        crud.update_user_streak(test_id, 5, yesterday)
        
        streak_before, date_before = crud.get_user_streak(test_id)
        print(f"📅 ДО сброса: streak={streak_before}, дата={date_before} (вчера)")
        
        # Симулируем полуночный сброс
        process_daily_reset(test_id)
        
        # Проверяем результат
        streak_after, date_after = crud.get_user_streak(test_id)
        print(f"🌅 ПОСЛЕ сброса: streak={streak_after}, дата={date_after}")
        
        if streak_after == 5:
            print("✅ Тест 1 ПРОЙДЕН: Streak НЕ сбросился (тест был вчера)")
        else:
            print(f"❌ Тест 1 ПРОВАЛЕН: streak={streak_after}, ожидалось 5")
            return False
        
        # Тест 2: Устанавливаем streak на позавчерашнюю дату  
        day_before_yesterday = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        crud.update_user_streak(test_id, 7, day_before_yesterday)
        
        streak_before2, date_before2 = crud.get_user_streak(test_id)
        print(f"📅 ДО сброса: streak={streak_before2}, дата={date_before2} (позавчера)")
        
        # Симулируем полуночный сброс
        process_daily_reset(test_id)
        
        # Проверяем результат
        streak_after2, date_after2 = crud.get_user_streak(test_id)
        print(f"🌅 ПОСЛЕ сброса: streak={streak_after2}, дата={date_after2}")
        
        if streak_after2 == 0:
            print("✅ Тест 2 ПРОЙДЕН: Streak СБРОСИЛСЯ (тест был позавчера)")
            return True
        else:
            print(f"❌ Тест 2 ПРОВАЛЕН: streak={streak_after2}, ожидалось 0")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

def fix_crud_reset_function():
    """Также исправляет функцию reset_user_streak в database/crud.py"""
    try:
        # Читаем файл
        with open('database/crud.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем есть ли уже исправленная версия
        if 'ИСПРАВЛЕННАЯ версия' in content:
            print("✅ Функция reset_user_streak уже обновлена")
            return True
        
        # Ищем и заменяем функцию
        old_function_start = 'def reset_user_streak(chat_id: int):'
        
        if old_function_start in content:
            print("📝 Обновляем функцию reset_user_streak...")
            
            # Новая функция
            new_function = '''def reset_user_streak(chat_id: int):
    """Сбрасывает количество дней подряд до 0. ИСПРАВЛЕННАЯ версия."""
    try:
        logger.debug(f"Resetting streak for user {chat_id}")
        update_user_streak(chat_id, 0, None)
        logger.info(f"Reset streak for user {chat_id}")
        
        # Проверяем что сброс прошел успешно
        verify_streak, verify_date = get_user_streak(chat_id)
        if verify_streak != 0:
            logger.error(f"Streak reset verification failed for user {chat_id}. Expected: 0, Got: {verify_streak}")
        else:
            logger.debug(f"Streak reset verified for user {chat_id}: {verify_streak}")
            
    except Exception as e:
        logger.error(f"Error resetting streak for user {chat_id}: {e}")'''
        
            # Находим начало и конец старой функции
            lines = content.split('\n')
            start_idx = None
            end_idx = None
            
            for i, line in enumerate(lines):
                if line.strip().startswith('def reset_user_streak(chat_id: int):'):
                    start_idx = i
                    break
            
            if start_idx is not None:
                # Ищем конец функции
                for i in range(start_idx + 1, len(lines)):
                    if lines[i].strip() and not lines[i].startswith('    ') and not lines[i].startswith('\t'):
                        if lines[i].strip().startswith('def ') or lines[i].strip().startswith('class '):
                            end_idx = i
                            break
                
                if end_idx is None:
                    end_idx = len(lines)
                
                # Заменяем функцию
                new_lines = lines[:start_idx] + new_function.split('\n') + lines[end_idx:]
                new_content = '\n'.join(new_lines)
                
                # Записываем файл
                with open('database/crud.py', 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print("✅ Функция reset_user_streak обновлена в database/crud.py")
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ Ошибка обновления database/crud.py: {e}")
        return False

if __name__ == "__main__":
    print("🔧 ТЕСТИРОВАНИЕ С ПЕРЕЗАГРУЗКОЙ МОДУЛЕЙ")
    print("=" * 50)
    
    # Сначала обновляем функцию в crud.py
    fix_crud_reset_function()
    
    # Затем тестируем с перезагрузкой
    if test_midnight_reset_with_reload():
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("✅ Система дней подряд работает корректно!")
    else:
        print("\n❌ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        print("❌ Требуется дополнительная отладка")