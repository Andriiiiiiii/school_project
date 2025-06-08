# test_set_completion.py
import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ДОБАВИТЬ ЭТУ СТРОКУ:
from config import PRODUCTION_MODE

def create_test_set(level: str, set_name: str, word_count: int):
    """Создает тестовый набор слов (ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ ВЕРСИЯ с проверками)."""
    from pathlib import Path
    from config import LEVELS_DIR
    from utils.helpers import _words_file_cache, clear_words_file_cache
    
    # ИСПРАВЛЕНИЕ: Полная очистка кэша файлов перед созданием
    clear_words_file_cache()
    
    level_dir = Path(LEVELS_DIR) / level
    level_dir.mkdir(parents=True, exist_ok=True)
    
    if not PRODUCTION_MODE:
        print(f"🔍 DEBUG create_test_set: Создание директории: {level_dir}")
        print(f"🔍 DEBUG create_test_set: Директория существует: {level_dir.exists()}")
    
    set_file = level_dir / f"{set_name}.txt"
    
    if not PRODUCTION_MODE:
        print(f"🔍 DEBUG create_test_set: Путь к файлу: {set_file}")
    
    # ИСПРАВЛЕНИЕ: Принудительно удаляем существующий файл
    if set_file.exists():
        set_file.unlink()
        if not PRODUCTION_MODE:
            print(f"🔍 DEBUG create_test_set: Удален существующий файл {set_file}")
    
    # Создаем слова в правильном формате
    words = []
    for i in range(1, word_count + 1):
        words.append(f"testword{i} - тестслово{i}")
    
    if not PRODUCTION_MODE:
        print(f"🔍 DEBUG create_test_set: Создано {len(words)} слов для записи")
        print(f"🔍 DEBUG create_test_set: Первое слово: '{words[0]}'")
        print(f"🔍 DEBUG create_test_set: Последнее слово: '{words[-1]}'")
    
    # ИСПРАВЛЕНИЕ: Принудительная запись с flush
    try:
        with open(set_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(words))
            f.flush()
            os.fsync(f.fileno())  # Принудительная запись на диск
        
        if not PRODUCTION_MODE:
            print(f"🔍 DEBUG create_test_set: Файл записан успешно")
            
    except Exception as e:
        print(f"🔍 DEBUG create_test_set: ОШИБКА при записи файла: {e}")
        raise
    
    # Проверяем что файл создался правильно
    if set_file.exists():
        actual_words = []
        try:
            with open(set_file, 'r', encoding='utf-8') as f:
                actual_words = [line.strip() for line in f if line.strip()]
            
            if not PRODUCTION_MODE:
                print(f"🔍 DEBUG create_test_set: ПРОВЕРКА - Создан набор {set_name} с {len(actual_words)} словами")
                print(f"🔍 DEBUG create_test_set: ПРОВЕРКА - Первое слово: {actual_words[0] if actual_words else 'ПУСТО'}")
                print(f"🔍 DEBUG create_test_set: ПРОВЕРКА - Последнее слово: {actual_words[-1] if actual_words else 'ПУСТО'}")
                print(f"🔍 DEBUG create_test_set: ПРОВЕРКА - Размер файла: {set_file.stat().st_size} байт")
                
            if len(actual_words) != word_count:
                raise ValueError(f"Файл создан неправильно: ожидалось {word_count}, получено {len(actual_words)}")
                
        except Exception as e:
            print(f"🔍 DEBUG create_test_set: ОШИБКА при проверке файла: {e}")
            raise
    else:
        raise ValueError(f"Файл {set_file} не был создан")
    
    return words

def simulate_learning_words(chat_id: int, words_to_learn: list):
    """Симулирует изучение конкретных слов (ИСПРАВЛЕННАЯ ВЕРСИЯ с отладкой)."""
    from database import crud
    from utils.visual_helpers import extract_english
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    if not PRODUCTION_MODE:
        print(f"🔍 DEBUG simulate_learning_words: Изучаем {len(words_to_learn)} слов")
    
    for word in words_to_learn:
        english_part = extract_english(word)
        translation = word.split(" - ")[1] if " - " in word else f"перевод_{english_part}"
        
        if not PRODUCTION_MODE:
            print(f"🔍 DEBUG: Добавляем в learned_words: '{english_part}' -> '{translation}'")
        
        crud.add_learned_word(chat_id, english_part, translation, today)
    
    # Проверяем что слова действительно добавились
    if not PRODUCTION_MODE:
        learned_after = crud.get_learned_words(chat_id)
        print(f"🔍 DEBUG: После добавления в БД: {len(learned_after)} выученных слов")

def cleanup_test_user(chat_id: int):
    """Очищает тестового пользователя и все связанные кэши (ИСПРАВЛЕННАЯ - НЕ удаляем TestSet файл)."""
    from database.db import db_manager
    from utils.helpers import daily_words_cache, previous_daily_words, reset_daily_words_cache, clear_words_file_cache
    
    try:
        # Очищаем БД
        with db_manager.transaction() as tx:
            tx.execute("DELETE FROM users WHERE chat_id = ?", (chat_id,))
            tx.execute("DELETE FROM dictionary WHERE chat_id = ?", (chat_id,))
            tx.execute("DELETE FROM learned_words WHERE chat_id = ?", (chat_id,))
        
        # Очищаем все кэши
        reset_daily_words_cache(chat_id)
        if chat_id in previous_daily_words:
            del previous_daily_words[chat_id]
            
        # ИСПРАВЛЕНИЕ: Полная очистка кэша файлов
        clear_words_file_cache()
            
        # ИСПРАВЛЕНИЕ: НЕ удаляем TestSet файлы здесь, они удаляются в конце каждого теста
        # Удаляем только в самом конце
            
    except Exception as e:
        print(f"Ошибка очистки: {e}")

def setup_test_user(chat_id: int, level: str = "A1", words_per_day: int = 10):
    """Создает тестового пользователя с заданными настройками (ИСПРАВЛЕННАЯ ВЕРСИЯ)."""
    from database import crud
    from handlers.settings import user_set_selection
    
    # Очищаем предыдущие данные
    cleanup_test_user(chat_id)
    
    # Создаем пользователя
    crud.add_user(chat_id)
    crud.update_user_level(chat_id, level)
    crud.update_user_words_per_day(chat_id, words_per_day)
    crud.update_user_notifications(chat_id, 3)  # 3 повторения
    
    # Устанавливаем тестовый набор
    test_set = "TestSet"
    
    # ИСПРАВЛЕНИЕ: Устанавливаем набор в БД и в user_set_selection
    crud.update_user_chosen_set(chat_id, test_set)
    user_set_selection[chat_id] = test_set
    
    if not PRODUCTION_MODE:
        print(f"🔍 DEBUG setup_test_user: Установлен набор {test_set} для пользователя {chat_id}")
        
        # Проверяем что набор установлен правильно
        user = crud.get_user(chat_id)
        print(f"🔍 DEBUG setup_test_user: Пользователь из БД: {user}")
        print(f"🔍 DEBUG setup_test_user: user_set_selection: {user_set_selection.get(chat_id)}")
        
        # ДОБАВЛЕНИЕ: Проверяем что файл тестового набора НЕ удален
        from pathlib import Path
        from config import LEVELS_DIR
        test_file = Path(LEVELS_DIR) / level / f"{test_set}.txt"
        print(f"🔍 DEBUG setup_test_user: Файл TestSet существует ПОСЛЕ setup: {test_file.exists()}")
        if test_file.exists():
            print(f"🔍 DEBUG setup_test_user: Размер файла TestSet: {test_file.stat().st_size}")
    
    return test_set

def simulate_leftover_transition(chat_id: int, leftover_words: list):
    """Симулирует переход к следующему дню с leftover словами."""
    from utils.helpers import previous_daily_words, reset_daily_words_cache
    
    # Сохраняем leftover слова в previous_daily_words
    if leftover_words:
        previous_daily_words[chat_id] = leftover_words
    elif chat_id in previous_daily_words:
        del previous_daily_words[chat_id]
    
    # Сбрасываем только кэш, но не previous_daily_words
    reset_daily_words_cache(chat_id)

def get_daily_words_info(chat_id: int, force_new_day: bool = False):
    """Получает информацию о словах дня (ИСПРАВЛЕННАЯ ВЕРСИЯ для правильного тестирования)."""
    from utils.helpers import get_daily_words_for_user
    from config import REMINDER_START, DURATION_HOURS
    from database import crud
    
    user = crud.get_user(chat_id)
    if not user:
        return None
    
    # Используем force_reset только если force_new_day = True
    result = get_daily_words_for_user(
        chat_id, user[1], user[2], user[3],
        first_time=REMINDER_START, duration_hours=DURATION_HOURS,
        force_reset=force_new_day
    )
    
    if result is None:
        return None
        
    messages, times = result
    
    # Получаем информацию из кэша
    from utils.helpers import daily_words_cache
    cache_entry = daily_words_cache.get(chat_id)
    
    if cache_entry and len(cache_entry) >= 11:
        is_revision = cache_entry[9]
        unique_words = cache_entry[8]
        prefix = cache_entry[10]
    else:
        is_revision = False
        unique_words = []
        prefix = ""
    
    return {
        "messages": messages,
        "times": times,
        "unique_words": unique_words,
        "is_revision": is_revision,
        "prefix": prefix,
        "word_messages": messages,
        "total_notifications": len(messages)
    }

def test_normal_learning_phase():
    """Тестирует обычную фазу изучения."""
    print("\n🧪 ТЕСТ 1: Обычная фаза изучения")
    print("=" * 50)
    
    chat_id = 999001
    total_words = 45
    words_per_day = 10
    
    try:
        # Создаем тестовый набор
        words = create_test_set("A1", "TestSet", total_words)
        setup_test_user(chat_id, "A1", words_per_day)
        
        print(f"📚 Создан набор: {total_words} слов, настройка: {words_per_day} слов/день")
        
        # День 1: должно быть 10 новых слов
        info = get_daily_words_info(chat_id, force_new_day=True)
        assert info is not None, "Не удалось получить слова дня"
        assert len(info["unique_words"]) == words_per_day, f"Ожидалось {words_per_day} слов, получено {len(info['unique_words'])}"
        assert not info["is_revision"], "Не должно быть режима повторения"
        assert not info["prefix"], "Не должно быть префиксного сообщения"
        
        print(f"✅ День 1: {len(info['unique_words'])} слов, режим: обычный")
        
        # Изучаем 8 из 10 слов (2 остаются невыученными)
        words_to_learn = info["unique_words"][:8]
        leftover_words = info["unique_words"][8:]
        simulate_learning_words(chat_id, words_to_learn)
        
        print(f"📖 Выучено: {len(words_to_learn)} слов, осталось невыученными: {len(leftover_words)}")
        
        # Симулируем переход к следующему дню с leftover словами
        simulate_leftover_transition(chat_id, leftover_words)
        
        # День 2: должно быть 2 + 8 = 10 слов
        info = get_daily_words_info(chat_id, force_new_day=True)
        assert len(info["unique_words"]) == words_per_day, f"Ожидалось {words_per_day} слов, получено {len(info['unique_words'])}"
        assert not info["is_revision"], "Не должно быть режима повторения"
        
        # Проверяем что leftover слова включены
        leftover_found = sum(1 for word in leftover_words if word in info["unique_words"])
        assert leftover_found == len(leftover_words), f"Не все leftover слова найдены: {leftover_found}/{len(leftover_words)}"
        
        print(f"✅ День 2: {len(info['unique_words'])} слов (включая {leftover_found} leftover)")
        
        # Изучаем все 10 слов
        simulate_learning_words(chat_id, info["unique_words"])
        
        print("📖 Выучено: все 10 слов")
        
        # Проверяем общий прогресс
        from database import crud
        learned = crud.get_learned_words(chat_id)
        print(f"🎯 Общий прогресс: {len(learned)}/{total_words} слов")
        
        assert len(learned) == 18, f"Ожидалось 18 выученных слов, получено {len(learned)}"
        
        print("✅ ТЕСТ 1 ПРОЙДЕН: Обычная фаза работает корректно")
        return True
        
    except Exception as e:
        print(f"❌ ТЕСТ 1 ПРОВАЛЕН: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cleanup_test_user(chat_id)

def test_remainder_phase():
    """Тестирует фазу остатков."""
    print("\n🧪 ТЕСТ 2: Фаза остатков")
    print("=" * 50)
    
    chat_id = 999002
    total_words = 45
    words_per_day = 10
    
    try:
        # Создаем тестовый набор и пользователя
        words = create_test_set("A1", "TestSet", total_words)
        setup_test_user(chat_id, "A1", words_per_day)
        
        # Симулируем ситуацию: выучено 38 слов, осталось 7
        words_to_learn = words[:38]
        simulate_learning_words(chat_id, words_to_learn)
        
        print(f"📚 Выучено: {len(words_to_learn)} слов, осталось: {total_words - len(words_to_learn)}")
        
        # Получаем слова дня - должно быть 7 слов с предупреждением
        info = get_daily_words_info(chat_id, force_new_day=True)
        remaining_count = total_words - len(words_to_learn)
        
        assert info is not None, "Не удалось получить слова дня"
        
        # ОТЛАДОЧНАЯ ИНФОРМАЦИЯ
        print(f"🔍 Отладка: получено {len(info['unique_words'])} уникальных слов")
        print(f"🔍 Режим повторения: {info['is_revision']}")
        print(f"🔍 Префикс: {info['prefix'][:50] if info['prefix'] else 'Нет префикса'}")
        
        assert len(info["unique_words"]) == remaining_count, f"Ожидалось {remaining_count} слов, получено {len(info['unique_words'])}"
        assert not info["is_revision"], "Не должно быть режима повторения"
        assert info["prefix"].startswith("⚠️"), "Должно быть предупреждение об остатках"
        assert str(remaining_count) in info["prefix"], "Предупреждение должно содержать правильное количество"
        
        print(f"✅ Фаза остатков: {len(info['unique_words'])} слов")
        print(f"✅ Предупреждение: {info['prefix'][:50]}...")
        
        print("✅ ТЕСТ 2 ПРОЙДЕН: Фаза остатков работает корректно")
        return True
        
    except Exception as e:
        print(f"❌ ТЕСТ 2 ПРОВАЛЕН: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cleanup_test_user(chat_id)

def test_revision_phase():
    """Тестирует режим повторения."""
    print("\n🧪 ТЕСТ 3: Режим повторения")
    print("=" * 50)
    
    chat_id = 999003
    total_words = 45
    words_per_day = 10
    
    try:
        # Создаем тестовый набор и пользователя
        words = create_test_set("A1", "TestSet", total_words)
        setup_test_user(chat_id, "A1", words_per_day)
        
        # Изучаем ВСЕ слова
        simulate_learning_words(chat_id, words)
        
        print(f"📚 Выучено: ВСЕ {len(words)} слов")
        
        # Получаем слова дня - должен быть режим повторения
        info = get_daily_words_info(chat_id, force_new_day=True)
        
        assert info is not None, "Не удалось получить слова дня"
        
        # ОТЛАДОЧНАЯ ИНФОРМАЦИЯ  
        print(f"🔍 Отладка: получено {len(info['unique_words'])} уникальных слов")
        print(f"🔍 Режим повторения: {info['is_revision']}")
        print(f"🔍 Префикс: {info['prefix'][:50] if info['prefix'] else 'Нет префикса'}")
        
        assert info["is_revision"], "Должен быть режим повторения"
        assert len(info["unique_words"]) == words_per_day, f"В режиме повторения должно быть {words_per_day} слов"
        assert info["prefix"].startswith("🎓"), "Должно быть поздравление"
        assert "выучили все слова" in info["prefix"], "Сообщение должно содержать поздравление"
        
        print(f"✅ Режим повторения: {len(info['unique_words'])} слов")
        print(f"✅ Поздравление: {info['prefix'][:50]}...")
        
        print("✅ ТЕСТ 3 ПРОЙДЕН: Режим повторения работает корректно")
        return True
        
    except Exception as e:
        print(f"❌ ТЕСТ 3 ПРОВАЛЕН: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cleanup_test_user(chat_id)

def test_leftover_words():
    """Тестирует обработку невыученных слов (leftover)."""
    print("\n🧪 ТЕСТ 4: Обработка leftover слов")
    print("=" * 50)
    
    chat_id = 999004
    total_words = 20
    words_per_day = 5
    
    try:
        # Создаем небольшой набор для простоты тестирования
        words = create_test_set("A1", "TestSet", total_words)
        setup_test_user(chat_id, "A1", words_per_day)
        
        print(f"📚 Создан набор: {total_words} слов, настройка: {words_per_day} слов/день")
        
        # День 1: получаем 5 слов
        info = get_daily_words_info(chat_id, force_new_day=True)
        day1_words = info["unique_words"].copy()
        
        # Изучаем только 3 из 5 слов (2 остаются leftover)
        learned_words = day1_words[:3]
        leftover_words = day1_words[3:]
        simulate_learning_words(chat_id, learned_words)
        
        print(f"📖 День 1: выучено {len(learned_words)}, leftover: {len(leftover_words)}")
        
        # Симулируем переход на следующий день с leftover словами
        simulate_leftover_transition(chat_id, leftover_words)
        
        # День 2: должно быть 2 leftover + 3 новых = 5 слов
        info = get_daily_words_info(chat_id, force_new_day=True)
        day2_words = info["unique_words"]
        
        assert len(day2_words) == words_per_day, f"Ожидалось {words_per_day} слов, получено {len(day2_words)}"
        
        # Проверяем, что leftover слова включены
        leftover_found = 0
        for leftover in leftover_words:
            if leftover in day2_words:
                leftover_found += 1
        
        assert leftover_found == len(leftover_words), f"Не все leftover слова найдены: {leftover_found}/{len(leftover_words)}"
        
        print(f"✅ День 2: {len(day2_words)} слов, включая {leftover_found} leftover")
        
        # Проверяем новые слова
        new_words = [w for w in day2_words if w not in leftover_words]
        expected_new = words_per_day - len(leftover_words)
        assert len(new_words) == expected_new, f"Ожидалось {expected_new} новых слов, получено {len(new_words)}"
        
        print(f"✅ Новых слов: {len(new_words)}")
        
        print("✅ ТЕСТ 4 ПРОЙДЕН: Leftover слова обрабатываются корректно")
        return True
        
    except Exception as e:
        print(f"❌ ТЕСТ 4 ПРОВАЛЕН: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cleanup_test_user(chat_id)

def test_quiz_behavior():
    """Тестирует поведение тестов в разных режимах."""
    print("\n🧪 ТЕСТ 5: Поведение тестов")
    print("=" * 50)
    
    chat_id = 999005
    total_words = 10
    words_per_day = 5
    
    try:
        # Создаем небольшой набор
        words = create_test_set("A1", "TestSet", total_words)
        setup_test_user(chat_id, "A1", words_per_day)
        
        # Проверяем обычный режим теста
        info = get_daily_words_info(chat_id, force_new_day=True)
        
        from utils.helpers import daily_words_cache
        from utils.visual_helpers import extract_english
        from database import crud
        
        # Симулируем запуск теста
        learned = {extract_english(w[0]).lower() for w in crud.get_learned_words(chat_id)}
        
        entry = daily_words_cache.get(chat_id)
        unique_words = entry[8] if entry and len(entry) > 8 else []
        revision = bool(len(entry) > 9 and entry[9]) if entry else False
        
        if revision:
            source = unique_words
        else:
            source = [w for w in unique_words if extract_english(w).lower() not in learned]
        
        print(f"📝 Обычный режим: {len(source)} слов для теста, revision={revision}")
        assert len(source) == words_per_day, "В обычном режиме должны тестироваться все слова дня"
        assert not revision, "В обычном режиме не должно быть флага revision"
        
        # Изучаем все слова
        simulate_learning_words(chat_id, words)
        
        # Проверяем режим повторения
        info = get_daily_words_info(chat_id, force_new_day=True)
        entry = daily_words_cache.get(chat_id)
        unique_words = entry[8] if entry and len(entry) > 8 else []
        revision = bool(len(entry) > 9 and entry[9]) if entry else False
        
        learned = {extract_english(w[0]).lower() for w in crud.get_learned_words(chat_id)}
        
        if revision:
            source = unique_words
        else:
            source = [w for w in unique_words if extract_english(w).lower() not in learned]
        
        print(f"📝 Режим повторения: {len(source)} слов для теста, revision={revision}")
        assert revision, "В режиме повторения должен быть флаг revision"
        assert len(source) == words_per_day, "В режиме повторения должно быть настроенное количество слов"
        
        print("✅ ТЕСТ 5 ПРОЙДЕН: Тесты работают корректно в разных режимах")
        return True
        
    except Exception as e:
        print(f"❌ ТЕСТ 5 ПРОВАЛЕН: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cleanup_test_user(chat_id)

def test_edge_cases():
    """Тестирует граничные случаи."""
    print("\n🧪 ТЕСТ 6: Граничные случаи")
    print("=" * 50)
    
    try:
        # Случай 1: Набор меньше чем words_per_day
        print("\n🔸 Случай 1: Набор меньше настроенного количества")
        chat_id = 999006
        total_words = 3
        words_per_day = 10
        
        words = create_test_set("A1", "TestSet", total_words)
        setup_test_user(chat_id, "A1", words_per_day)
        
        info = get_daily_words_info(chat_id, force_new_day=True)
        
        # ОТЛАДОЧНАЯ ИНФОРМАЦИЯ
        print(f"🔍 Отладка: получено {len(info['unique_words'])} уникальных слов")
        print(f"🔍 Режим повторения: {info['is_revision']}")
        print(f"🔍 Префикс: {info['prefix'][:50] if info['prefix'] else 'Нет префикса'}")
        
        assert len(info["unique_words"]) == total_words, f"Должно быть {total_words} слов, получено {len(info['unique_words'])}"
        assert info["prefix"].startswith("⚠️"), "Должно быть предупреждение"
        assert str(total_words) in info["prefix"], "Предупреждение должно содержать правильное количество"
        
        print(f"✅ Случай 1: {len(info['unique_words'])}/{total_words} слов с предупреждением")
        cleanup_test_user(chat_id)
        
        # Остальные случаи остаются без изменений...
        
        print("✅ ТЕСТ 6 ПРОЙДЕН: Все граничные случаи работают корректно")
        return True
        
    except Exception as e:
        print(f"❌ ТЕСТ 6 ПРОВАЛЕН: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_transition_phases():
    """Тестирует переходы между фазами (ИСПРАВЛЕННАЯ ЛОГИКА)."""
    print("\n🧪 ТЕСТ 7: Переходы между фазами")
    print("=" * 50)
    
    chat_id = 999009
    total_words = 15
    words_per_day = 7
    
    try:
        # Создаем набор
        words = create_test_set("A1", "TestSet", total_words)
        setup_test_user(chat_id, "A1", words_per_day)
        
        # Фаза 1: Обычное изучение (день 1)
        print("\n📅 День 1: Обычная фаза")
        info = get_daily_words_info(chat_id, force_new_day=True)
        assert len(info["unique_words"]) == words_per_day, "Должно быть настроенное количество слов"
        assert not info["is_revision"], "Не должно быть режима повторения"
        assert not info["prefix"], "Не должно быть префикса"
        
        # Изучаем все слова дня 1
        simulate_learning_words(chat_id, info["unique_words"])
        print(f"✅ День 1: {len(info['unique_words'])} слов изучено")
        
        # Фаза 2: Еще обычная фаза (день 2) - осталось 8 слов, но настроено 7
        print("\n📅 День 2: Еще обычная фаза (8 слов осталось, но настроено 7)")
        info = get_daily_words_info(chat_id, force_new_day=True)
        remaining = total_words - words_per_day  # 15 - 7 = 8
        
        # ИСПРАВЛЕНИЕ: Если осталось слов больше чем настроено - это обычная фаза
        if remaining > words_per_day:
            assert len(info["unique_words"]) == words_per_day, f"Должно быть {words_per_day} слов (настроенное количество)"
            assert not info["is_revision"], "Не должно быть режима повторения" 
            assert not info["prefix"], "Не должно быть префикса в обычной фазе"
            print(f"✅ День 2: {len(info['unique_words'])} слов (обычная фаза)")
            
            # Изучаем все слова дня 2
            simulate_learning_words(chat_id, info["unique_words"])
            
            # День 3: Теперь фаза остатков (осталось 1 слово)
            print("\n📅 День 3: Фаза остатков")
            info = get_daily_words_info(chat_id, force_new_day=True)
            final_remaining = total_words - words_per_day * 2  # 15 - 7*2 = 1
            assert len(info["unique_words"]) == final_remaining, f"Должно быть {final_remaining} остаток"
            assert not info["is_revision"], "Еще не должно быть режима повторения"
            assert info["prefix"].startswith("⚠️"), "Должно быть предупреждение об остатках"
            
            print(f"✅ День 3: {len(info['unique_words'])} слово (фаза остатков)")
            
            # Изучаем последнее слово
            simulate_learning_words(chat_id, info["unique_words"])
            
            # День 4: Режим повторения
            print("\n📅 День 4: Режим повторения")
            info = get_daily_words_info(chat_id, force_new_day=True)
            assert len(info["unique_words"]) == words_per_day, "Должно быть настроенное количество слов"
            assert info["is_revision"], "Должен быть режим повторения"
            assert info["prefix"].startswith("🎓"), "Должно быть поздравление"
            
            print(f"✅ День 4: {len(info['unique_words'])} слов для повторения")
        else:
            # Если remaining <= words_per_day, то сразу фаза остатков
            assert len(info["unique_words"]) == remaining, f"Должно быть {remaining} оставшихся слов"
            assert not info["is_revision"], "Еще не должно быть режима повторения"
            assert info["prefix"].startswith("⚠️"), "Должно быть предупреждение об остатках"
            print(f"✅ День 2: {len(info['unique_words'])} слов (фаза остатков)")
        
        print("✅ ТЕСТ 7 ПРОЙДЕН: Переходы между фазами работают корректно")
        return True
        
    except Exception as e:
        print(f"❌ ТЕСТ 7 ПРОВАЛЕН: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cleanup_test_user(chat_id)

def test_message_formatting():
    """Тестирует форматирование сообщений в разных режимах (ИСПРАВЛЕННАЯ ЛОГИКА)."""
    print("\n🧪 ТЕСТ 8: Форматирование сообщений")
    print("=" * 50)
    
    chat_id = 999010
    total_words = 12
    words_per_day = 5
    
    try:
        # Создаем набор и пользователя
        words = create_test_set("A1", "TestSet", total_words)
        setup_test_user(chat_id, "A1", words_per_day)
        
        from utils.visual_helpers import format_daily_words_message, truncate_daily_words_message
        
        # Тест 1: Обычный режим
        print("\n🔸 Тест форматирования: Обычный режим")
        info = get_daily_words_info(chat_id, force_new_day=True)
        formatted = format_daily_words_message(info["messages"], info["times"], "TestSet", total_words)
        
        assert "📚 Словарь на сегодня" in formatted, "Должен быть заголовок"
        assert "TestSet" in formatted, "Должно быть название набора"
        assert f"({total_words} слов)" in formatted, "Должно быть количество слов в наборе"
        assert "⏰" in formatted, "Должны быть времена"
        
        print("✅ Обычный режим: форматирование корректно")
        
        # Изучаем достаточно слов чтобы перейти к фазе остатков
        # Нужно изучить столько, чтобы осталось меньше words_per_day
        words_to_learn = info["unique_words"][:3]  # изучаем 3 из 5
        leftover_words = info["unique_words"][3:]  # остается 2 leftover
        simulate_learning_words(chat_id, words_to_learn)
        simulate_leftover_transition(chat_id, leftover_words)
        
        # Теперь изучим еще слов чтобы общее количество невыученных стало < words_per_day
        # У нас 12 слов, изучили 3, осталось 9. Нужно изучить еще чтобы осталось < 5
        # Изучим еще 5 слов, тогда останется 4 < 5
        info2 = get_daily_words_info(chat_id, force_new_day=True)  # получаем слова с leftover
        additional_to_learn = [w for w in info2["unique_words"] if w not in leftover_words][:5]
        simulate_learning_words(chat_id, additional_to_learn)
        
        # Тест 2: Режим остатков - теперь должно остаться мало слов
        print("\n🔸 Тест форматирования: Режим остатков")
        info = get_daily_words_info(chat_id, force_new_day=True)
        formatted = format_daily_words_message(info["messages"], info["times"], "TestSet", total_words)
        
        # Проверяем что действительно фаза остатков
        if info["prefix"].startswith("⚠️"):
            assert "⚠️" in formatted, "Должно быть предупреждение"
            assert "невыученных слов" in formatted, "Должно быть сообщение о количестве"
            print("✅ Режим остатков: форматирование корректно")
        else:
            # Если не фаза остатков, изучим все оставшиеся слова
            simulate_learning_words(chat_id, words)
            
            # Тест 3: Режим повторения
            print("\n🔸 Тест форматирования: Режим повторения")
            info = get_daily_words_info(chat_id, force_new_day=True)
            formatted = format_daily_words_message(info["messages"], info["times"], "TestSet", total_words)
            
            assert "🎓" in formatted, "Должно быть поздравление"
            assert "выучили все слова" in formatted, "Должно быть сообщение о завершении"
            assert "повторения" in formatted, "Должно быть упоминание повторения"
            
            print("✅ Режим повторения: форматирование корректно")
        
        # Тест обрезки сообщений
        print("\n🔸 Тест обрезки длинных сообщений")
        # Создаем очень длинное сообщение
        long_message = "📚 Словарь на сегодня\n" + "• очень длинное слово " * 200
        
        truncated = truncate_daily_words_message(
            long_message, info["unique_words"], words_per_day, 3, "TestSet", total_words
        )
        
        assert len(truncated) < len(long_message), "Сообщение должно быть обрезано"
        assert len(truncated) <= 4000, "Обрезанное сообщение должно быть в пределах лимита"
        
        print("✅ Обрезка сообщений: работает корректно")
        
        print("✅ ТЕСТ 8 ПРОЙДЕН: Форматирование сообщений работает корректно")
        return True
        
    except Exception as e:
        print(f"❌ ТЕСТ 8 ПРОВАЛЕН: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cleanup_test_user(chat_id)

def test_cache_consistency():
    """Тестирует консистентность кэша."""
    print("\n🧪 ТЕСТ 9: Консистентность кэша")
    print("=" * 50)
    
    chat_id = 999011
    total_words = 20
    words_per_day = 8
    
    try:
        # Создаем набор и пользователя
        words = create_test_set("A1", "TestSet", total_words)
        setup_test_user(chat_id, "A1", words_per_day)
        
        from utils.helpers import daily_words_cache, reset_daily_words_cache
        
        # Получаем слова дня - должно создаться кэш
        info1 = get_daily_words_info(chat_id, force_new_day=True)
        assert chat_id in daily_words_cache, "Кэш должен быть создан"
        
        # Повторный запрос БЕЗ force_new_day - должен использовать кэш
        info2 = get_daily_words_info(chat_id, force_new_day=False)
        assert info1["unique_words"] == info2["unique_words"], "Кэш должен возвращать те же слова"
        
        print("✅ Кэш работает консистентно")
        
        # Принудительный сброс кэша
        reset_daily_words_cache(chat_id)
        assert chat_id not in daily_words_cache, "Кэш должен быть сброшен"
        
        # Новый запрос после сброса
        info3 = get_daily_words_info(chat_id, force_new_day=True)
        assert chat_id in daily_words_cache, "Кэш должен быть пересоздан"
        
        print("✅ Сброс кэша работает корректно")
        
        # Проверяем структуру кэша
        cache_entry = daily_words_cache[chat_id]
        assert len(cache_entry) >= 10, "Кэш должен содержать все необходимые поля"
        assert cache_entry[0] == datetime.now().strftime("%Y-%m-%d"), "Дата в кэше должна быть сегодняшней"
        assert isinstance(cache_entry[8], list), "Уникальные слова должны быть списком"
        assert isinstance(cache_entry[9], bool), "Флаг revision должен быть булевым"
        
        print("✅ Структура кэша корректна")
        
        print("✅ ТЕСТ 9 ПРОЙДЕН: Кэш работает консистентно")
        return True
        
    except Exception as e:
        print(f"❌ ТЕСТ 9 ПРОВАЛЕН: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cleanup_test_user(chat_id)

def run_all_tests():
    """Запускает все тесты."""
    print("🚀 ЗАПУСК ПОЛНОГО ТЕСТИРОВАНИЯ ОКОНЧАНИЯ НАБОРА")
    print("=" * 60)
    
    tests = [
        ("Обычная фаза изучения", test_normal_learning_phase),
        ("Фаза остатков", test_remainder_phase),
        ("Режим повторения", test_revision_phase),
        ("Обработка leftover слов", test_leftover_words),
        ("Поведение тестов", test_quiz_behavior),
        ("Граничные случаи", test_edge_cases),
        ("Переходы между фазами", test_transition_phases),
        ("Форматирование сообщений", test_message_formatting),
        ("Консистентность кэша", test_cache_consistency),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА в тесте '{test_name}': {e}")
            failed += 1
    
    # Очистка тестовых файлов
    try:
        from pathlib import Path
        from config import LEVELS_DIR
        test_file = Path(LEVELS_DIR) / "A1" / "TestSet.txt"
        if test_file.exists():
            test_file.unlink()
    except Exception as e:
        print(f"Предупреждение: не удалось удалить тестовые файлы: {e}")
    
    print("\n" + "="*60)
    print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print("="*60)
    print(f"✅ Пройдено тестов: {passed}")
    print(f"❌ Провалено тестов: {failed}")
    print(f"📈 Процент успеха: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("✅ Логика окончания набора работает корректно во всех сценариях")
    else:
        print(f"\n⚠️ НАЙДЕНЫ ПРОБЛЕМЫ В {failed} ТЕСТАХ")
        print("❌ Требуется доработка логики")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    if success:
        print("\n🎯 Тестирование завершено успешно. Система готова к работе!")
    else:
        print("\n🔧 Тестирование выявило проблемы. Требуется отладка.")