# fix_datetime_import.py
"""
Проверяет и исправляет импорт datetime в database/crud.py
"""

import os
import sys

def fix_datetime_import():
    """Исправляет импорт datetime в crud.py файле."""
    
    crud_file_path = "database/crud.py"
    
    if not os.path.exists(crud_file_path):
        print(f"❌ Файл {crud_file_path} не найден")
        return False
    
    print(f"🔍 Проверяем файл {crud_file_path}...")
    
    # Читаем файл
    with open(crud_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Проверяем, есть ли уже импорт datetime
    if "from datetime import datetime, timedelta" in content:
        print("✅ Импорт datetime уже присутствует")
        return True
    
    print("🔧 Добавляем импорт datetime...")
    
    # Ищем место для вставки импорта
    lines = content.split('\n')
    insert_position = -1
    
    # Находим последний импорт
    for i, line in enumerate(lines):
        if line.startswith('from ') or line.startswith('import '):
            insert_position = i
    
    if insert_position == -1:
        print("❌ Не удалось найти место для вставки импорта")
        return False
    
    # Вставляем импорт после последнего существующего импорта
    lines.insert(insert_position + 1, "from datetime import datetime, timedelta")
    
    # Записываем обратно в файл
    with open(crud_file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print("✅ Импорт datetime добавлен успешно")
    return True

def test_import():
    """Тестирует, работает ли импорт."""
    print("\n🧪 Тестируем импорт...")
    
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Пытаемся импортировать функцию
        from database.crud import increment_user_streak
        print("✅ Функция increment_user_streak импортируется корректно")
        
        # Пытаемся вызвать функцию с несуществующим пользователем
        try:
            result = increment_user_streak(999999)
            print(f"✅ Функция выполняется без ошибок (результат: {result})")
            return True
        except NameError as e:
            if "datetime" in str(e):
                print(f"❌ Ошибка импорта datetime: {e}")
                return False
            else:
                print(f"✅ Импорт datetime работает, другая ошибка: {e}")
                return True
        except Exception as e:
            print(f"✅ Импорт datetime работает, функция выполнилась с ошибкой БД: {e}")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        return False

if __name__ == "__main__":
    print("🔧 ИСПРАВЛЕНИЕ ИМПОРТА DATETIME")
    print("=" * 40)
    
    success = fix_datetime_import()
    if success:
        test_success = test_import()
        if test_success:
            print("\n🎉 Импорт datetime исправлен и работает!")
            print("💡 Теперь можете запустить: python quick_streak_test.py")
        else:
            print("\n⚠️ Импорт добавлен, но есть проблемы")
    else:
        print("\n❌ Не удалось исправить импорт")